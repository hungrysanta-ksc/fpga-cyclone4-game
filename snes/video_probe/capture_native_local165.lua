-- SPDX-License-Identifier: MIT
local stage,captured,shown=0,0,-1
local revealed=false
local log=assert(io.open(OUT_DIR..'/trace.tsv','w'))
local cases,start={},0
local function rd(a)return emu.read(a,emu.memType.snesWorkRam)end
local function word(a)return rd(a)+rd(a+1)*256 end
local function jsoncase(q)
 local commands={};for _,x in ipairs(q.commands)do commands[#commands+1]='['..table.concat(x,',')..']'end
 return string.format('{"status":%d,"count":%d,"payload":%d,"charged":%d,"ticks":%d,"service_calls":%d,"commands":[%s]}',q.status,q.count,q.payload,q.charged,q.ticks,q.service_calls,table.concat(commands,','))
end
emu.addMemoryCallback(function(a,v)return captured end,emu.callbackType.read,0x6000,0x6000)
emu.addMemoryCallback(function(a,v)
 local s=emu.getState();local line=s['ppu.scanline']
 if a==0x2100 then
  if revealed then assert((v&128)==0,'blank after reveal')end
  if v==15 then revealed=true end
 end
 if revealed and (a==0x2118 or a==0x2119 or a==0x2104 or a==0x2122)then assert(line>=225,'upload outside vblank '..line)end
 if a==0x7000 then assert(rd(0x1025)==3,'not uploaded');stage=v;shown=s.frameCount end
 if a==0x7002 then start=s.masterClock end
 if a==0x7003 then
  local q={status=rd(0x1025),count=word(0x1026),payload=word(0x102a),charged=word(0x1028),ticks=s.masterClock-start,service_calls=word(0x1036),commands={}}
  assert(q.count<=32)
  for i=0,q.count-1 do local b=0x1100+i*8;q.commands[#q.commands+1]={word(b),word(b+2),word(b+4),word(b+6)}end
  cases[#cases+1]=q;log:write('CASE '..v..' '..jsoncase(q)..'\n');log:flush()
 end
 if a==0x7004 then
  assert(v==0xa5 and captured==2 and #cases==9)
  local out={};for _,q in ipairs(cases)do out[#out+1]=jsoncase(q)end
  local f=assert(io.open(OUT_DIR..'/cases.json','w'));f:write('['..table.concat(out,',')..']');f:close();log:close();emu.stop(0)
 end
 if a==0x7000 or a==0x420b then log:write(table.concat({a,v,s.frameCount,line,s.masterClock},'\t')..'\n');log:flush()end
end,emu.callbackType.write,0,0xffff)
emu.addEventCallback(function()
 local s=emu.getState()
 if stage>captured and s.frameCount>shown+1 then
  local size=emu.getScreenSize();assert(size.width==256 and size.height==239)
  local buf=emu.getScreenBuffer();local f=assert(io.open(OUT_DIR..'/frame-'..stage..'.rgb','wb'))
  for y=0,size.height-1 do local row={}
   for x=0,size.width-1 do local v=buf[y*size.width+x+1];row[#row+1]=string.char((v>>16)&255,(v>>8)&255,v&255)end
   f:write(table.concat(row))
  end
  f:close();captured=stage
 end
 if s.frameCount>120 then error('local diff watchdog')end
end,emu.eventType.endFrame)
