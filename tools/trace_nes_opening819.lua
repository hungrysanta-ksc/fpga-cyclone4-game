-- Run under Mesen --testRunner from an empty output directory. No input.
local out = assert(io.open("mask819.csv", "w"))
out:write("frame,clock,line,dot,mask\n")
local mask = -1
emu.addMemoryCallback(function(a, v)
  if a % 8 ~= 1 or mask == v then return end
  local s = emu.getState()
  out:write(string.format("%d,%d,%d,%d,%d\n", s.frameCount, s.masterClock,
    s["ppu.scanline"], s["ppu.cycle"], v))
  mask = v
end, emu.callbackType.write, 0x2000, 0x3fff, emu.cpuType.nes, emu.memType.nesMemory)
local count = 0
emu.addEventCallback(function()
  count = count + 1
  if count == 3600 then out:close(); emu.stop(0) end
end, emu.eventType.endFrame)
