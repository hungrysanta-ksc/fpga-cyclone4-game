-- The parent supplies OUT. The ROM and controller state are read-only.
local frame, handle, samples = 0, nil, {}
local trace = assert(io.open(OUT.."/reads.bin", "wb"))
local windows = assert(io.open(OUT.."/windows.txt", "w"))
local last, changed, count = nil, 0, 0
local released = {a=false,b=false,start=false,select=false,up=false,down=false,left=false,right=false}
local function read_chr(address, value)
 local s = emu.getState()
 local y, dot = s["ppu.scanline"], s["ppu.cycle"]
 if y<7 or y>=231 or dot<257 or dot>320 or (dot%8~=5 and dot%8~=7) then return end
 local oy = assert(s["ppu.secondarySpriteRam"..(((dot-257)//8)*4)])
 local height = s["ppu.control.largeSprites"] and 16 or 8
 if oy==255 or y<oy or y-oy>=height then return end
 local p = emu.convertAddress(address,emu.memType.nesPpuMemory,emu.cpuType.nes)
 assert(p and p.memType==emu.memType.nesChrRom)
 samples[#samples+1] = string.pack("<I4B",p.address,value)
end
emu.addEventCallback(function()
 frame=frame+1
 if frame%60==30 then
  handle=emu.addMemoryCallback(read_chr,emu.callbackType.read,0,0x1fff,emu.cpuType.nes,emu.memType.nesPpuMemory)
 end
end,emu.eventType.startFrame)
emu.addEventCallback(function()
 emu.setInput(released,0);emu.setInput(released,1)
 if handle then
  emu.removeMemoryCallback(handle,emu.callbackType.read,0,0x1fff,emu.cpuType.nes,emu.memType.nesPpuMemory)
  handle=nil
  trace:write(string.pack("<I4I4",frame,#samples),table.concat(samples))
  trace:flush()
  samples={}
 end
 if frame%6==0 then
  local screen,h=emu.getScreenBuffer(),0
  for i=1,#screen,113 do h=(h*31+screen[i]) & 0x7fffffff end
  if frame>60 then count=count+1;if h~=last then changed=changed+1 end end
  last=h
 end
 if frame==1800 or frame==3600 then
  windows:write(frame," ",changed," ",count,"\n");changed=0;count=0
 end
 if frame==3600 then trace:close();windows:close();emu.stop(0) end
end,emu.eventType.endFrame)
