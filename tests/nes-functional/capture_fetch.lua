-- SPDX-License-Identifier: MIT. Observation only; callbacks never return replacement values.
local trace=assert(io.open(OUT_DIR..'/trace.tsv','w'))
local frames=assert(io.open(OUT_DIR..'/frames.tsv','w'))
local function row(kind,a,v,physical,memtype)
 local s=emu.getState()
 if kind=='read' and s.frameCount<FIRST_FRAME-1 then return end
 trace:write(table.concat({kind,s.frameCount,s['ppu.scanline'],s['ppu.cycle'],s['ppu.masterClock'],s.masterClock,a,v,physical,memtype,s['ppu.control.backgroundPatternAddr']},'\t')..'\n')
end
emu.addMemoryCallback(function(a,v)
 local p=emu.convertAddress(a,emu.memType.nesPpuMemory,emu.cpuType.nes)
 row('read',a,v,p.address,p.memType)
end,emu.callbackType.read,0,0x1fff,emu.cpuType.nes,emu.memType.nesPpuMemory)
emu.addMemoryCallback(function(a,v) row('ctrl',a,v,-1,-1) end,emu.callbackType.write,0x2000,0x2000,emu.cpuType.nes)
emu.addEventCallback(function()
 local s=emu.getState()
 if s.frameCount>=FIRST_FRAME then
  local size=emu.getScreenSize();local buf=emu.getScreenBuffer()
  frames:write(table.concat({s.frameCount,s['ppu.scanline'],s['ppu.cycle'],s['ppu.masterClock'],s.masterClock,s['ppu.control.backgroundPatternAddr'],emu.read(1,emu.memType.nesInternalRam),size.width,size.height,emu.memType.nesChrRom},'\t')..'\n');frames:flush()
  local f=assert(io.open(string.format('%s/frame-%03d.rgb',OUT_DIR,s.frameCount),'wb'))
  for y=0,size.height-1 do
   local pixels={}
   for x=0,size.width-1 do local c=buf[y*size.width+x+1];pixels[#pixels+1]=string.char((c>>16)&255,(c>>8)&255,c&255) end
   f:write(table.concat(pixels))
  end
  f:close()
 end
 trace:flush()
 if s.frameCount==LAST_FRAME then trace:close();frames:close();emu.stop(0) end
end,emu.eventType.endFrame)
