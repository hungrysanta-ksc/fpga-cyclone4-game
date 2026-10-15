-- SPDX-License-Identifier: MIT
-- Held mailbox only: no WRAM/PPU/ACK injection. CPU owns all display writes.
local packet, pendingAck, previousScreen=nil,nil,nil
local rejected=false
local ordinal,commits,shown,acks,pads,chunks,held=1,0,-1,0,0,0,0
local ack={};local revealed=false;local spc=0
local log=assert(io.open(OUT_DIR..'/bus.tsv','w'))
local function rd(a)return emu.read(a,emu.memType.snesWorkRam)end
local function word(a)return rd(a)+rd(a+1)*256 end
local function pb(i)return assert(packet):byte(i+1)end
local function pw(i)return pb(i)+pb(i+1)*256 end
local function publish(bytes)
 local name=string.format(OUT_DIR..'/ack-%04d',ordinal)
 local f=assert(io.open(name..'.tmp','wb'));f:write(bytes);f:close();assert(os.rename(name..'.tmp',name..'.bin'))
 packet=nil;ordinal=ordinal+1;pendingAck=nil
end
emu.addMemoryCallback(function(a,v)
 if a==0x6000 then return packet and not pendingAck and 1 or 0 end
 if a==0x6001 then
  if packet and pb(0)==3 and pw(8)==13 then
   if MODE=='stop_copy' and chunks>0 then return 128 end
   if MODE=='stop_final' and rd(0x1025)==2 then return 128 end
  end
  return 0
 end
 local n=packet and #packet or 0;return a==0x6004 and n&255 or n>>8
end,emu.callbackType.read,0x6000,0x6005)
emu.addMemoryCallback(function(a,v)
 assert(packet and not pendingAck,'unowned packet read');local i=a-0x400000;assert(i<#packet,'packet overread');return pb(i)
end,emu.callbackType.read,0x400000,0x4000ff)
emu.addMemoryCallback(function(a,v)return a==0x4218 and 0 or 4 end,emu.callbackType.read,0x4218,0x4219)
local function write(a,v)
 local st=emu.getState()
 if a==0x6003 then assert(v==4);pads=pads+1 end
 if a==0x7001 then assert(v==0xa9);spc=v end
 if a==0x2100 then if revealed then assert(v==15,'visible forced blank')end;if v==15 then assert(st['ppu.scanline']>=225,'reveal outside vblank');revealed=true end end
 if revealed and (a==0x2118 or a==0x2119 or a==0x2122 or a==0x2104)then assert(st['ppu.scanline']>=225,'DMA outside vblank '..a..' '..st['ppu.scanline'])end
 if a==0x420b and packet and pb(0)==3 and (rd(0x1025)==0xe2 or rd(0x1025)==0xe3)then chunks=chunks+1 end
 if a>=0x6010 and a<=0x601b then ack[a-0x6010+1]=v end
 if a==0x601c then
  assert(v==0xa5 and packet and not pendingAck and #ack==12)
  for i=2,9 do assert(ack[i+1]==pb(i),'token mismatch')end
  assert(ack[2]==pb(0) and ack[11]==0x65 and ack[12]==0x9a)
  acks=acks+1;log:write(table.concat({ordinal,pb(0),pw(8),ack[1],word(0x1026),word(0x1032),st.masterClock,st['ppu.scanline']},'\t')..'\n');log:flush()
  local bytes=string.char(table.unpack(ack));ack={}
  if bytes:byte(1)==1 then
   assert(rd(0x1025)==3 and revealed and st['ppu.scanline']>=225,'early display ACK');commits=commits+1;shown=st.frameCount;pendingAck=bytes
  elseif bytes:byte(1)>=0xe0 then rejected=true;shown=st.frameCount;pendingAck=bytes
  else publish(bytes)end
 end
end
for _,range in ipairs({{0x2100,0x2122},{0x420b,0x420b},{0x6002,0x601c},{0x7001,0x7001}})do
 emu.addMemoryCallback(write,emu.callbackType.write,range[1],range[2])
end
emu.addEventCallback(function()
 local st=emu.getState()
 if previousScreen and packet and pb(0)==3 and (rd(0x1025)==0xe2 or rd(0x1025)==0xe3)then
  local now=emu.getScreenBuffer();for i=1,#now do assert(now[i]==previousScreen[i],'changed active frame before flip')end;held=held+1
 end
 if pendingAck and st.frameCount>shown+1 then
  local size=emu.getScreenSize();assert(size.width==256 and size.height==239)
  local buf=emu.getScreenBuffer();local f=assert(io.open(OUT_DIR..'/frame-'..commits..'.rgb','wb'))
  for y=0,238 do local row={};for x=0,255 do local v=buf[y*256+x+1];row[#row+1]=string.char((v>>16)&255,(v>>8)&255,v&255)end;f:write(table.concat(row))end
  f:close()
  if rejected then for i=1,#buf do assert(buf[i]==previousScreen[i],'rejected candidate changed display')end
  else previousScreen=buf end
  publish(pendingAck)
 end
 if not packet then local f=io.open(string.format(OUT_DIR..'/req-%04d.bin',ordinal),'rb');if f then packet=f:read('*a');f:close()end end
 local f=io.open(OUT_DIR..'/producer-done.txt','r')
 if f then
  f:close();assert(spc==0xa9 and pads>0 and acks==ordinal-1);assert(commits==(MODE=='normal' and 7 or ((MODE=='max' or MODE=='raw_first') and 2 or 1)))
  if MODE=='normal' then assert(chunks>0 and held>0)end
  if MODE=='max' then assert(chunks==7 and held==7,'max seven bounded chunks')end
  local o=assert(io.open(OUT_DIR..'/consumer-result.json','w'));o:write(string.format('{"passed":true,"commits":%d,"acks":%d,"pads":%d,"chunks":%d,"held_frames":%d}',commits,acks,pads,chunks,held));o:close();log:close();emu.stop(0)
 end
 if st.frameCount>4000 then error('client watchdog')end
end,emu.eventType.endFrame)
