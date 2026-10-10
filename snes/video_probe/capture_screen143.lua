-- SPDX-License-Identifier: MIT
-- Actual65816/PPU execution with a separately modeled044 packet MMIO supplier.
local f=assert(io.open(PACKET_FILE,'rb'));local payload=f:read('*a');f:close()
assert(#payload==6024)
local state,available,consumed,nextseq,seq,commits,reads=0,0,0,1,0,0,0
local cfg={[2]=0,[3]=0,[4]=0,[5]=0}
local regs={};local lastpage=0;local count=0
local seenphase,phasefirst={},{}
local frames=assert(io.open(OUT_DIR..'/frames.tsv','w'))
local trace=assert(io.open(OUT_DIR..'/trace.tsv','w'))
local function clk()return emu.getState().masterClock end
local function rd(a)return emu.read(a,emu.memType.snesWorkRam)end
local function update()
 if state==2 and clk()>=available then state=1 end
 if state==8 and clk()>=available then state=0;consumed=0;commits=commits+1;nextseq=nextseq+1 end
end
local function log(k,a,v)
 local s=emu.getState()
 trace:write(table.concat({k,a,v,s.masterClock,s.frameCount,s['ppu.scanline'],s['ppu.hClock']},'\t')..'\n')
end
emu.addMemoryCallback(function(a,v)
 update();local n=a-0x6000;local r=0
 if n==0 then r=(state==8 and 2 or state)
 elseif n>=2 and n<=5 then r=cfg[n]
 elseif n==6 then r=(MODE=='bad_length' and 0 or 0xd8)
 elseif n==7 then r=7
 elseif n==8 then r=consumed&255
 elseif n==9 then r=consumed>>8
 elseif n==11 then r=1 end
 log('R',a,r);return r
end,emu.callbackType.read,0x6000,0x600c)
emu.addMemoryCallback(function(a,v)
 update();assert(state==1 and consumed<2008 and seq<=3)
 assert(a==0x408000+consumed)
 local value=payload:byte((seq-1)*2008+consumed+1);assert(value~=nil)
 if MODE=='bad_header' and consumed==0 then value=0 end
 consumed=consumed+1;reads=reads+1;log('D',a,value);return value
end,emu.callbackType.read,0x408000,0x408bff)
emu.addMemoryCallback(function(a,v)
 local lo=a&0xffff
 if a>=0x6000 and a<=0x6009 then
  update();log('W',a,v);local n=a-0x6000
  if n>=2 and n<=5 then assert(state==0);cfg[n]=v
  elseif n==0 and v==1 then
   assert(state==0 and cfg[2]+cfg[3]*256==1);seq=cfg[4]+cfg[5]*256;assert(seq==nextseq)
   state=2;available=clk()+(seq<=3 and 21478 or 10000000)
  elseif n==0 and v==2 then assert(state==1 and consumed==2008);state=8;available=clk()+200
  else error('unexpected command')end
 end
 if lo>=0x4300 and lo<=0x4306 then regs[lo]=v end
 if lo==0x420b then
  trace:write(table.concat({'DMA',regs[0x4300] or 0,regs[0x4301] or 0,regs[0x4304] or 0,
   (regs[0x4302] or 0)+256*(regs[0x4303] or 0),(regs[0x4305] or 0)+256*(regs[0x4306] or 0),clk()},'\t')..'\n')
 end
 if lo==0x1fe6 then log('PHASE',lo,v)end
 if lo==0x7000 or lo==0x7001 then log('MILESTONE',lo,v)end
end,emu.callbackType.write,0,0x3fffff)
emu.addEventCallback(function()
 local phase=rd(0x1fd8);local frame=emu.getState().frameCount
 if phase>=0x31 and phase<=0x33 and not seenphase[phase] then
  phasefirst[phase]=phasefirst[phase] or frame
  if frame>=phasefirst[phase]+2 then
   seenphase[phase]=true;local size=emu.getScreenSize();local buf=emu.getScreenBuffer()
   local f=assert(io.open(string.format('%s/phase-%d.rgb',OUT_DIR,phase),'wb'))
   for y=0,size.height-1 do local row={}
    for x=0,size.width-1 do local c=buf[y*size.width+x+1];row[#row+1]=string.char((c>>16)&255,(c>>8)&255,c&255)end
    f:write(table.concat(row))
   end
   f:close();log('PHASE_CAPTURE',phase,frame)
  end
 end
 if rd(0x1ff0)~=165 then return end
 local page=rd(0x1fe0);local err=rd(0x1fe8)
 if page==lastpage and err==0 then return end
 lastpage=page;count=count+1
 local s=emu.getState();local size=emu.getScreenSize();local buf=emu.getScreenBuffer()
 frames:write(table.concat({count,page,err,size.width,size.height,s.frameCount},'\t')..'\n');frames:flush()
 local image=assert(io.open(string.format('%s/frame-%d.rgb',OUT_DIR,count),'wb'))
 for y=0,size.height-1 do local row={}
  for x=0,size.width-1 do local c=buf[y*size.width+x+1];row[#row+1]=string.char((c>>16)&255,(c>>8)&255,c&255)end
  image:write(table.concat(row))
 end
 image:close()
 if count==3 or err~=0 then
  local m=assert(io.open(OUT_DIR..'/model.tsv','w'));m:write(table.concat({commits,reads,err},'\t'));m:close()
  frames:close();trace:close();emu.stop(0)
 end
end,emu.eventType.endFrame)
