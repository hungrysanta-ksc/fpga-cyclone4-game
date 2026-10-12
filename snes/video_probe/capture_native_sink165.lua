-- SPDX-License-Identifier: MIT
-- Immutable packet/ACK bus model. C process supplies packets while real65816
-- consumes them. No host-injected ACK, WRAM data, comparison or DMA commands.
local packet=nil
local ordinal,commits,captured,ackcount,pads,spc=1,0,0,0,0,nil
local pendingAck=nil
local ack={}
local shown=-1
local revealed=false
local log=assert(io.open(OUT_DIR..'/bus.tsv','w'))
local function rd(a)return emu.read(a,emu.memType.snesWorkRam)end
local function word(a)return rd(a)+rd(a+1)*256 end
local function packetbyte(i)return assert(packet):byte(i+1)end
local function packetword(i)return packetbyte(i)+packetbyte(i+1)*256 end
local function publish(bytes)
 local name=string.format(OUT_DIR..'/ack-%04d',ordinal)
 local f=assert(io.open(name..'.tmp','wb'));f:write(bytes);f:close();assert(os.rename(name..'.tmp',name..'.bin'))
 packet=nil;ordinal=ordinal+1;pendingAck=nil
end
emu.addMemoryCallback(function(a,v)
 if a==0x6000 then return packet and not pendingAck and 1 or 0 end
 if a==0x6001 then
  return MODE=='stop' and packet and packetbyte(0)==3 and packetword(8)==15 and rd(0x1025)==1 and 128 or 0
 end
 local n=packet and #packet or 0
 return a==0x6004 and n&255 or n>>8
end,emu.callbackType.read,0x6000,0x6005)
emu.addMemoryCallback(function(a,v)
 assert(packet and not pendingAck,'read without owned packet')
 local i=a-0x400000;assert(i<#packet,'read beyond admitted packet')
 return packetbyte(i)
end,emu.callbackType.read,0x400000,0x4000ff)
emu.addMemoryCallback(function(a,v)return a==0x4218 and 0 or 4 end,emu.callbackType.read,0x4218,0x4219)
emu.addMemoryCallback(function(a,v)
 local st=emu.getState()
 if a==0x6003 then assert(v==4,'held DOWN sample');pads=pads+1 end
 if a==0x7001 then assert(v==0xa9,'SPC bootstrap');spc=v end
 if a==0x2100 then if revealed then assert(v==15,'post-reveal blank')end;if v==15 then revealed=true end end
 if revealed and (a==0x2118 or a==0x2119 or a==0x2122 or a==0x2104)then assert(st['ppu.scanline']>=225,'visible DMA outside vblank')end
 if a>=0x6010 and a<=0x601b then ack[a-0x6010+1]=v end
 if a==0x601c then
  assert(v==0xa5 and packet and not pendingAck and #ack==12,'ACK publish')
  for i=2,9 do assert(ack[i+1]==packetbyte(i),'ACK token mismatch')end
  assert(ack[2]==packetbyte(0) and ack[11]==0x65 and ack[12]==0x9a)
  ackcount=ackcount+1
  log:write(table.concat({ordinal,packetbyte(0),packetword(8),ack[1],word(0x1026),word(0x102a),st.masterClock,st['ppu.scanline']},'\t')..'\n');log:flush()
  local bytes=string.char(table.unpack(ack));ack={}
  if ack[1] then error('cleared ACK')end
  if bytes:byte(1)==1 then
   assert(rd(0x1025)==3 and revealed,'ACK before display completion')
   commits=commits+1;shown=st.frameCount;pendingAck=bytes
  else publish(bytes)end
 end
end,emu.callbackType.write,0,0xffff)
emu.addEventCallback(function()
 local st=emu.getState()
 if pendingAck and st.frameCount>shown+1 then
  local size=emu.getScreenSize();assert(size.width==256 and size.height==239)
  local buf=emu.getScreenBuffer();local f=assert(io.open(OUT_DIR..'/frame-'..commits..'.rgb','wb'))
  for y=0,size.height-1 do local row={}
   for x=0,size.width-1 do local v=buf[y*size.width+x+1];row[#row+1]=string.char((v>>16)&255,(v>>8)&255,v&255)end
   f:write(table.concat(row))
  end
  f:close();captured=commits;publish(pendingAck)
 end
 if not packet then
  local f=io.open(string.format(OUT_DIR..'/req-%04d.bin',ordinal),'rb')
  if f then packet=f:read('*a');f:close();assert(#packet>=16 and #packet<=256)end
 end
 local f=io.open(OUT_DIR..'/producer-done.txt','r')
 if f then
  f:close();assert(spc==0xa9 and pads>0 and ackcount==ordinal-1)
  assert(captured==(MODE=='stop' and 1 or 3))
  local o=assert(io.open(OUT_DIR..'/consumer-result.json','w'))
  o:write(string.format('{"passed":true,"commits":%d,"acks":%d,"pads":%d,"spc":%d}',commits,ackcount,pads,spc));o:close();log:close();emu.stop(0)
 end
 if st.frameCount>5000 then error('sink watchdog')end
end,emu.eventType.endFrame)
