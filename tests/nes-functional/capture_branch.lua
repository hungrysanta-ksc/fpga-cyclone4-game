-- SPDX-License-Identifier: MIT. Observational callbacks, no replacement values.
local f=assert(io.open(OUT_DIR..'/branch-bus.tsv','w'))
local done=false
local function row(k,a,v)
 if done then return end
 local s=emu.getState()
 f:write(table.concat({k,s.masterClock,a,v,emu.read(0,emu.memType.nesInternalRam)},'\t')..'\n')
 if k=='W' and a==0 and v==255 then done=true;f:close();emu.stop(0) end
end
emu.addMemoryCallback(function(a,v)row('R',a,v)end,emu.callbackType.read,0,0xffff,emu.cpuType.nes)
emu.addMemoryCallback(function(a,v)row('W',a,v)end,emu.callbackType.write,0,0xffff,emu.cpuType.nes)
emu.addMemoryCallback(function(a,v)row('X',a,v)end,emu.callbackType.exec,0,0xffff,emu.cpuType.nes)
emu.addEventCallback(function()if emu.getState().frameCount>3 then f:close();emu.stop(1)end end,emu.eventType.endFrame)
