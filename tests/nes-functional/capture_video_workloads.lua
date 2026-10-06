-- SPDX-License-Identifier: MIT. Observational NES workload capture, never changes emulated state.
local trace=assert(io.open(OUT_DIR..'/trace.tsv','w'))
local frames=assert(io.open(OUT_DIR..'/frames.tsv','w'))
local mask=0
local ctrl=0
local sx=0
local sy=0
local latch=0
local function record(kind,a,v,p)
 local s=emu.getState()
 if kind=='read' and s.frameCount<6 then return end
 trace:write(table.concat({kind,s.frameCount,s['ppu.scanline'],s['ppu.cycle'],s['ppu.masterClock'],s.masterClock,a,v,p},'\t')..'\n')
end
emu.addMemoryCallback(function(a,v)
 local p=emu.convertAddress(a,emu.memType.nesPpuMemory,emu.cpuType.nes)
 record('read',a,v,p.address)
end,emu.callbackType.read,0,0x1fff,emu.cpuType.nes,emu.memType.nesPpuMemory)
emu.addMemoryCallback(function(a,v)
 if a==0x2000 then ctrl=v end
 if a==0x2001 then mask=v end
 if a==0x2005 then
  if latch==0 then sx=v else sy=v end
  latch=1-latch
 end
 if a==0x2006 then latch=1-latch end
 record('ppu_write',a,v,-1)
end,emu.callbackType.write,0x2000,0x2007,emu.cpuType.nes)
emu.addMemoryCallback(function(a,v) latch=0 end,emu.callbackType.read,0x2002,0x2002,emu.cpuType.nes)
emu.addMemoryCallback(function(a,v)record('mapper_write',a,v,-1)end,emu.callbackType.write,0x8000,0xffff,emu.cpuType.nes)
emu.addEventCallback(function()
 local s=emu.getState()
 if s.frameCount>=6 then
  local size=emu.getScreenSize();local buf=emu.getScreenBuffer()
  frames:write(table.concat({s.frameCount,size.width,size.height,mask,ctrl,sx,sy,
    emu.read(0,emu.memType.nesInternalRam),emu.read(1,emu.memType.nesInternalRam),emu.read(3,emu.memType.nesInternalRam)},'\t')..'\n');frames:flush()
  local f=assert(io.open(string.format('%s/frame-%03d.rgb',OUT_DIR,s.frameCount),'wb'))
  for y=0,239 do
   local row={}
   for x=0,255 do local c=buf[y*256+x+1];row[#row+1]=string.char((c>>16)&255,(c>>8)&255,c&255)end
   f:write(table.concat(row))
  end
  f:close()
 end
 trace:flush()
 if s.frameCount==9 then trace:close();frames:close();emu.stop(0) end
end,emu.eventType.endFrame)