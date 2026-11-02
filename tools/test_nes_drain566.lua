-- SPDX-License-Identifier: MIT
-- The runner substitutes the paths, cut point and SPI bounds from the ARM trace.
local input = assert(io.open(@ARRIVALS@, "r"))
local out = assert(io.open(@TRACE@, "w"))
local cut, bypass = @CUT@, @BYPASS@
local stopAt, restartAt = @STOP@, @START@
local romVector = @VECTOR@
local packets = {}
local function unhex(s) return (s:gsub("..",function(c) return string.char(tonumber(c,16)) end)) end
for line in input:lines() do
  local t,p,b = line:match("^(%d+)\t([^\t]+)\t(.*)$")
  local row = {clock=tonumber(t), packet=unhex(p), data=unhex(b)}
  packets[#packets+1] = row
  if row.packet:byte(1)==7 and row.packet:byte(17)==1 then break end
end
input:close()
assert(#packets[#packets].data==320)
local idx, reads, fresh, resetSeen, booted = 1,0,false,false,false
local packet, tripClock, clockOrigin, vectorCount = nil,nil,0,0
local bytes, epoch, mask, ackStatus, ack = {}, "old",0,nil,{}
local function now() return emu.getState().masterClock end
local function note(s,v)
  out:write(string.format("%s,%d,%d,%d,%d\n",s,now(),idx,reads,v or 0))
  out:flush()
end
local function trip(label)
  if not tripClock and idx==#packets and label==cut then
    tripClock=now()
    note("cancel")
    if not bypass then emu.reset() end
  end
end
local function owner()
  if fresh then return "fresh" end
  if not tripClock then return "old" end
  if bypass or now()-tripClock>=restartAt then return "unread" end
  if now()-tripClock>=stopAt then return "stopped" end
  return "old"
end
emu.addEventCallback(function()
  assert(tripClock and not bypass and not resetSeen)
  resetSeen=true
  note("reset_applied")
  -- Discard prior ordinary queue state. Serve a fresh cold stream from BEGIN.
  fresh=true;idx=1;packet=nil;reads=0;bytes={};mask=0;ack={};ackStatus=nil;clockOrigin=now()
end,emu.eventType.reset)
emu.addMemoryCallback(function()
  vectorCount=vectorCount+1
  if resetSeen then booted=true;note("reset_vector") end
end,emu.callbackType.exec,romVector,romVector)
emu.addMemoryCallback(function(a)
  if a==0x6000 then
    if tripClock and not fresh then return 0 end
    if not packet and packets[idx] and now()-clockOrigin>=packets[idx].clock then
      packet=packets[idx];reads=0;bytes={};mask=0;ack={};ackStatus=nil
    end
    return packet and 1 or 0
  end
  if a==0x6001 then return 0 end
  local n=packet and #packet.packet or 0
  return a==0x6004 and n&255 or n>>8
end,emu.callbackType.read,0x6000,0x6005)
emu.addMemoryCallback(function(a)
  -- Even during cancellation, supply the former head's bytes to stress stale writes.
  return assert(packet.packet:byte(a-0x400000+1))
end,emu.callbackType.read,0x400000,0x4000ff)
emu.addMemoryCallback(function() return 0 end,emu.callbackType.read,0x4218,0x4219)
emu.addMemoryCallback(function(a)
  local p=packet.packet
  local d={1,p:byte(2),p:byte(15),p:byte(16),p:byte(11),p:byte(12),p:byte(9),p:byte(10),p:byte(17,20)}
  return d[a-0x6040+1]
end,emu.callbackType.read,0x6040,0x604b)
emu.addMemoryCallback(function(a)
  assert(a==0x400800+reads and reads<#packet.data)
  reads=reads+1
  if reads==#packet.data-1 then trip("one_byte_left") end
  if reads==#packet.data and idx==#packets then
    note(fresh and "fresh_last_read" or "old_last_read")
    trip("last_read")
  end
  return packet.data:byte(reads)
end,emu.callbackType.read,0x400800,0x400fff)
emu.addMemoryCallback(function() trip("before_first_store") end,emu.callbackType.exec,@STORE@,@STORE@)
emu.addMemoryCallback(function(a,v)
  local w=owner()
  if epoch~=w then epoch=w;mask=0;bytes={} end
  if idx==#packets then note(w.."_write",a*256+v) end
  if a<0x6050 then
    local i=a-0x604c
    bytes[i+1]=v;mask=mask|(1<<i)
    if i==1 then trip("two_token_bytes") end
  else
    assert(v==0xa5)
    if w=="old" or w=="fresh" or w=="unread" then
      assert(mask==15 and string.char(table.unpack(bytes))==packet.packet:sub(17,20))
      if w=="unread" then
        assert(bypass);note("unread_retired");out:close();emu.stop(0)
      elseif idx==#packets and fresh then
        assert(booted and reads==#packet.data);note("fresh_commit")
      end
    end
  end
end,emu.callbackType.write,0x604c,0x6050)
emu.addMemoryCallback(function(a,v)
  if tripClock and not fresh then return end
  if a<0x601c then ack[a-0x6010+1]=v;return end
  assert(v==0xa5 and #ack==12 and ack[1]==0 and ack[2]==packet.packet:byte(1))
  assert(string.char(table.unpack(ack,3,10))==packet.packet:sub(3,10) and ack[11]==0x65 and ack[12]==0x9a)
  if fresh and idx==#packets then note("fresh_packet_ack");out:close();emu.stop(0) end
  idx=idx+1;packet=nil
end,emu.callbackType.write,0x6010,0x601c)
local frames=0
emu.addEventCallback(function() frames=frames+1;assert(frames<140,"timeout index "..idx) end,emu.eventType.endFrame)
