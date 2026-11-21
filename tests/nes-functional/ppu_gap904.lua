-- Count pattern-bus reads without changing the NES state or supplying input.
local log = assert(io.open(OUT, "w"))
local reads, frame, id = 0, 0, nil
emu.addEventCallback(function()
  frame = emu.getState().frameCount
  reads = 0
  if frame == 3300 then
    id = emu.addMemoryCallback(function() reads = reads + 1 end,
      emu.callbackType.read, 0, 0x1fff, emu.cpuType.nes, emu.memType.nesPpuMemory)
  end
end, emu.eventType.startFrame)
emu.addEventCallback(function()
  local s = emu.getState()
  if frame >= 3300 then
    log:write(frame, ",", s.frameCount, ",", s.masterClock, ",", reads, "\n")
  end
  if frame == 3500 then
    log:close()
    emu.stop(0)
  end
end, emu.eventType.endFrame)
