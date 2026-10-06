-- SPDX-License-Identifier: MIT. Read-only observation of real SNES execution.
local trace=assert(io.open(OUT_DIR..'/trace.tsv','w'))
local meta=assert(io.open(OUT_DIR..'/frames.tsv','w'))
local count=0
local regs={}
local function rd(a) return emu.read(a,emu.memType.snesWorkRam) end
local function log(kind,value)
 local s=emu.getState()
 local fields={kind,value,s.masterClock,s.frameCount,s['ppu.scanline'],s['ppu.hClock'],rd(0x1fe0),rd(0x1fe1),rd(0x1fe5),
  regs[0x4301] or 0,(regs[0x4305] or 0)+256*(regs[0x4306] or 0),
  (regs[0x2116] or 0)+256*(regs[0x2117] or 0),regs[0x4304] or 0,
  (regs[0x4302] or 0)+256*(regs[0x4303] or 0),regs[0x2107] or 0,regs[0x2115] or 0}
 trace:write(table.concat(fields,'\t')..'\n');trace:flush()
end
emu.addMemoryCallback(function(address,value)
 local a=address & 0xffff
 if a==0x2115 or a==0x2107 or a==0x2116 or a==0x2117 or (a>=0x4300 and a<=0x4306) then regs[a]=value end
 if a==0x210d then log('scroll',value) end
 if a==0x2115 then log('vmain',value) end
 if a==0x1fe6 then log('phase',value) end
 if a==0x420b then log('dma',value) end
 if a==0x2107 then log('mapbase',value) end
 if a==0x2100 then log('brightness',value) end
end,emu.callbackType.write,0,0x3fffff)
emu.addEventCallback(function()
 if rd(0x1ff0)~=165 then return end
 local s=emu.getState();local size=emu.getScreenSize();local buf=emu.getScreenBuffer()
 meta:write(table.concat({count,s.frameCount,s.masterClock,rd(0x1fe0),rd(0x1fe5),size.width,size.height},'\t')..'\n');meta:flush()
 local f=assert(io.open(string.format('%s/frame-%03d.rgb',OUT_DIR,count),'wb'))
 for y=0,size.height-1 do
  local row={}
  for x=0,size.width-1 do local c=buf[y*size.width+x+1];row[#row+1]=string.char((c>>16)&255,(c>>8)&255,c&255) end
  f:write(table.concat(row))
 end
 f:close();count=count+1
 if count==4 then trace:close();meta:close();emu.stop(0) end
end,emu.eventType.endFrame)