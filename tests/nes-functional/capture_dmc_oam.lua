-- SPDX-License-Identifier: MIT. Observational callbacks only.
assert(emu.memType.nesSpriteRam)
local f=assert(io.open(OUT_DIR..'/dma-bus.tsv','w'));local o=assert(io.open(OUT_DIR..'/oam.tsv','w'));local done=false
local function row(k,a,v)
 if done then return end
 local s=emu.getState();local n=emu.read(0,emu.memType.nesInternalRam)
 f:write(table.concat({k,s.masterClock,a,v,n},'\t')..'\n')
 if k=='W' and a==32 then
  o:write(table.concat({'E',n,emu.read(16,emu.memType.nesInternalRam),-1},'\t')..'\n')
  for i=0,255 do o:write(table.concat({'O',n,i,emu.read(i,emu.memType.nesSpriteRam)},'\t')..'\n')end
 end
 if k=='W' and a==0 and v==255 then done=true;f:close();o:close();emu.stop(0)end
end
emu.addMemoryCallback(function(a,v)row('R',a,v)end,emu.callbackType.read,0,0xffff,emu.cpuType.nes)
emu.addMemoryCallback(function(a,v)row('W',a,v)end,emu.callbackType.write,0,0xffff,emu.cpuType.nes)
emu.addMemoryCallback(function(a,v)row('X',a,v)end,emu.callbackType.exec,0,0xffff,emu.cpuType.nes)
emu.addEventCallback(function()if emu.getState().frameCount>4 then f:close();o:close();emu.stop(1)end end,emu.eventType.endFrame)
