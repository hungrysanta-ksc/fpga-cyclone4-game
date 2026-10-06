-- SPDX-License-Identifier: MIT
-- Explicit MMIO device MODEL backed by bytes captured from an actual RTL execution.
-- Runs real SNES CPU and PPU DMA in Mesen; not simultaneous RTL/emulator co-simulation.
local f=assert(io.open(RTL_BYTES,'rb'));local payload=f:read('*a');f:close()
assert(#payload==14336)
local trace=assert(io.open(OUT_DIR..'/trace.tsv','w'))
local frames=assert(io.open(OUT_DIR..'/frames.tsv','w'))
local cfg={[2]=0,[3]=0,[4]=0,[5]=0}
local state=0;local available=0;local consumed=0;local nextseq=1;local seq=0
local commits=0;local reads=0;local lastpage=-1;local count=0;local regs={}
local function clk()return emu.getState().masterClock end
local function rd(a)return emu.read(a,emu.memType.snesWorkRam)end
local function update()
 if state==2 and clk()>=available then state=1 end
 if state==8 and clk()>=available then state=0;consumed=0;commits=commits+1;nextseq=nextseq+1 end
end
local function log(kind,a,v)
 local s=emu.getState()
 trace:write(table.concat({kind,a,v,s.masterClock,s.frameCount,s['ppu.scanline'],s['ppu.hClock']},'\t')..'\n')
end
emu.addMemoryCallback(function(a,v)
 update()
 local n=a-0x6000
 local result=0
 if n==0 then result=(state==8 and 2 or state)
 elseif n>=2 and n<=5 then result=cfg[n]
 elseif n==6 then result=(MODE=='bad_length' and 1 or 0)
 elseif n==7 then result=8
 elseif n==8 then result=consumed&255
 elseif n==9 then result=consumed>>8 end
 log('R',a,result);return result
end,emu.callbackType.read,0x6000,0x600a)
emu.addMemoryCallback(function(a,v)
 update()
 assert(state==1 and consumed<2048,'payload before READY or overread')
 assert(a==0x408000+consumed,'nonsequential DMA source')
 local value=payload:byte((seq-1)*2048+consumed+1);assert(value~=nil)
 consumed=consumed+1;reads=reads+1;log('D',a,value);return value
end,emu.callbackType.read,0x408000,0x408bff)
emu.addMemoryCallback(function(a,v)
 local lo=a&0xffff
 if a>=0x6000 and a<=0x6009 then
  update();log('W',a,v)
  local n=a-0x6000
  if n>=2 and n<=5 then assert(state==0);cfg[n]=v
  elseif n==0 and v==1 then
   assert(state==0);assert(cfg[2]+cfg[3]*256==1);seq=cfg[4]+cfg[5]*256;assert(seq==nextseq)
   if MODE~='absent' then state=2;available=clk()+21478 end
  elseif n==0 and v==2 then
   assert(state==1 and consumed==2048,'early commit');state=8;available=clk()+200
  else error('unexpected host command')end
 end
 if lo>=0x4300 and lo<=0x4306 then regs[lo]=v end
 if lo==0x420b then
  log('M',lo,v)
  trace:write(table.concat({'A',regs[0x4304] or 0,(regs[0x4302] or 0)+256*(regs[0x4303] or 0),
   (regs[0x4305] or 0)+256*(regs[0x4306] or 0),regs[0x4300] or 0,regs[0x4301] or 0,clk()},'\t')..'\n')
 end
 if lo==0x1fe6 or lo==0x2100 then log('S',lo,v)end
end,emu.callbackType.write,0,0x3fffff)
emu.addEventCallback(function()
 if rd(0x1ff0)~=165 then return end
 local page=rd(0x1fe0)
 if page==lastpage then return end
 lastpage=page
 local s=emu.getState();local size=emu.getScreenSize();local buf=emu.getScreenBuffer()
 frames:write(table.concat({count,s.frameCount,s.masterClock,page,rd(0x1fe8),size.width,size.height},'\t')..'\n');frames:flush()
 local image=assert(io.open(string.format('%s/frame-%03d.rgb',OUT_DIR,count),'wb'))
 for y=0,size.height-1 do
  local row={}
  for x=0,size.width-1 do local color=buf[y*size.width+x+1];row[#row+1]=string.char((color>>16)&255,(color>>8)&255,color&255)end
  image:write(table.concat(row))
 end
 image:close();count=count+1
 if (MODE=='normal' and commits==6) or (MODE~='normal' and page==4) then
  local meta=assert(io.open(OUT_DIR..'/model.tsv','w'))
  meta:write(table.concat({commits,reads,rd(0x1fe8)},'\t')..'\n');meta:close()
  trace:close();frames:close();emu.stop(0)
 end
end,emu.eventType.endFrame)
