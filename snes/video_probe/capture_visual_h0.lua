-- SPDX-License-Identifier: MIT. Read-only runtime observer.
local trace=assert(io.open(OUT_DIR..'/trace.tsv','w'))
local frames=assert(io.open(OUT_DIR..'/frames.tsv','w'))
local count=0
local previous=0
local age=0
local visits=0
local regs={}
local function rd(a)return emu.read(a,emu.memType.snesWorkRam)end
emu.addMemoryCallback(function(address,value)
 local a=address&0xffff
 if a>=0x4300 and a<=0x4306 then regs[a]=value end
 if a==0x1fe6 or a==0x420b or a==0x2100 or a==0x210b then
  local s=emu.getState()
  trace:write(table.concat({a,value,s.masterClock,s.frameCount,s['ppu.scanline'],s['ppu.hClock'],
   rd(0x1fe0),regs[0x4301] or 0,(regs[0x4305] or 0)+256*(regs[0x4306] or 0)},'\t')..'\n')
  trace:flush()
 end
end,emu.callbackType.write,0,0x3fffff)
emu.addEventCallback(function()
 if rd(0x1ff0)~=165 then return end
 local page=rd(0x1fe0)
 if page~=previous then previous=page;age=0;visits=visits+1 else age=age+1 end
 if age~=0 and age~=30 then return end
 local s=emu.getState();local size=emu.getScreenSize();local buf=emu.getScreenBuffer()
 frames:write(table.concat({count,s.frameCount,s.masterClock,page,age,size.width,size.height},'\t')..'\n');frames:flush()
 local f=assert(io.open(string.format('%s/frame-%03d.rgb',OUT_DIR,count),'wb'))
 for y=0,size.height-1 do
  local row={}
  for x=0,size.width-1 do local c=buf[y*size.width+x+1];row[#row+1]=string.char((c>>16)&255,(c>>8)&255,c&255)end
  f:write(table.concat(row))
 end
 f:close();count=count+1
 if visits==4 then trace:close();frames:close();emu.stop(0)end
end,emu.eventType.endFrame)
