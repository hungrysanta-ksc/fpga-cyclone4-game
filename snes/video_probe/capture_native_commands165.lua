-- SPDX-License-Identifier: MIT
local stage,captured,shown=0,0,-1
local revealed=false
local log=assert(io.open(OUT_DIR..'/trace.tsv','w'))
emu.addMemoryCallback(function(a,v)return captured>=1 and 1 or 0 end,emu.callbackType.read,0x6000,0x6000)
emu.addMemoryCallback(function(a,v)
 local s=emu.getState();local line=s['ppu.scanline']
 if a==0x2100 then
  if revealed then assert((v&128)==0,'blank after reveal')end
  if v==15 then revealed=true end
 end
 if revealed and (a==0x2118 or a==0x2119 or a==0x2104 or a==0x2122)then
  assert(line>=225,'PPU upload outside vblank '..line)
 end
 if a==0x7000 then stage=v;shown=s.frameCount end
 if a==0x7000 or a==0x420b or a==0x2100 then
  log:write(table.concat({a,v,s.frameCount,line,s.masterClock},'\t')..'\n');log:flush()
 end
end,emu.callbackType.write,0,0xffff)
emu.addEventCallback(function()
 local s=emu.getState()
 if stage>captured and s.frameCount>shown+1 then
  local size=emu.getScreenSize();assert(size.width==256 and size.height==239)
  local buf=emu.getScreenBuffer();local f=assert(io.open(OUT_DIR..'/frame-'..stage..'.rgb','wb'))
  for y=0,size.height-1 do local row={}
   for x=0,size.width-1 do local c=buf[y*size.width+x+1];row[#row+1]=string.char((c>>16)&255,(c>>8)&255,c&255)end
   f:write(table.concat(row))
  end
  f:close();captured=stage
  if captured==2 then log:close();emu.stop(0)end
 end
 if s.frameCount>60 then error('native commands watchdog')end
end,emu.eventType.endFrame)
