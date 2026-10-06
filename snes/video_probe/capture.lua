-- SPDX-License-Identifier: MIT
-- Generated OUT_DIR prefix is provided by run_probe.py. Capture only: no PPU writes.
local frames=0
emu.addEventCallback(function()
 frames=frames+1
 if frames==10 or frames==11 then
  local size=emu.getScreenSize()
  local buf=emu.getScreenBuffer()
  local f=assert(io.open(OUT_DIR..'/frame-'..frames..'.txt','w'))
  f:write(size.width..' '..size.height..'\n')
  f:write('marker '..emu.read(0x1ff0,emu.memType.snesWorkRam)..'\n')
  for y=0,size.height-1 do
   local row={}
   for x=0,size.width-1 do row[#row+1]=string.format('%06x',buf[y*size.width+x+1]) end
   f:write(table.concat(row)..'\n')
  end
  f:close()
  local png=assert(io.open(OUT_DIR..'/frame-'..frames..'.png','wb'))
  png:write(emu.takeScreenshot());png:close()
  if frames==11 then emu.stop(0) end
 end
end,emu.eventType.endFrame)
