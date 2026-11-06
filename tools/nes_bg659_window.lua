do
local mode,target=MODE659,TARGET659
local jobs={JOBS659};local sub={CODE659};local starts={STARTS659};local ends={ENDS659}
local period=PERIOD659;local chr=file('chr659.bin');local trace=assert(io.open(ROOT..'/bus659.csv','w'))
trace:write('g,event,clock,line,address,value,words,consumed\n')
local words,consumed,readyAt,nextFree,base,bad=0,0,nil,0,-1,false
local patched=false
local function clock()return emu.getState().masterClock end
local function log(e,addr,v)local s=emu.getState();trace:write(string.format('%d,%s,%d,%d,%d,%d,%d,%d\n',word(0x1226),e,s.masterClock,s['ppu.scanline'],addr,v,words,consumed));trace:flush()end
local function selectTime(t)
 if mode=='open' then return t+6 end
 local n=t%period;local lo,hi=1,#starts+1
 while lo<hi do local mid=(lo+hi)//2;if starts[mid]<n then lo=mid+1 else hi=mid end end
 return t-n+(lo>#starts and period+ends[1] or ends[lo])
end
local function advance(t)
 while true do
  if readyAt then
   if readyAt>t then return end
   nextFree=readyAt+1;words=words+1;readyAt=nil
  elseif words<8 and words-consumed//2<2 then readyAt=selectTime(nextFree)
  else nextFree=t+1;return end
 end
end
local function wram(a,v)emu.write(a,v,emu.memType.snesWorkRam)end
local function replaceDMA(enable)
 local bytes=enable and {0x20,0x80,0x36} or {0x8d,0x0b,0x42}
 for i,v in ipairs(bytes)do wram(0x2c03+i,v)end
end
-- Inspect the operands prepared by the unmodified consumer, before LDA #1.
checkedMem527(function()
 local g=word(0x1226);local s=(regs[0x4302] or 0)+256*(regs[0x4303] or 0)
 local n=(regs[0x4305] or 0)+256*(regs[0x4306] or 0)
 local list=jobs[g]
 if not list or (target~=0 and g~=target) or not list[s] then return end
 assert(n%16==0 and n<=160 and regs[0x4304]==0x7f and regs[0x4301]==0x18)
 local off=0;for pos=s,s+n-1,16 do
  local tag=assert(list[pos]);local a=tag*16
  for i=0,15 do assert(chr:byte(a+i+1)==rd(0x10000+pos+i),'independent checked tile mismatch')end
  wram(0x3e00+off,a%256);wram(0x3e01+off,(a//256)%256);wram(0x3e02+off,0x50+a//65536);off=off+3
 end
 wram(0x0ee0,off);wram(0x0ee1,0)
 for i,v in ipairs(sub)do wram(0x367f+i,v)end
 replaceDMA(true);patched=true;log('enter',s,n)
end,emu.callbackType.exec,0x7e2c02)
checkedMem527(function()if patched then replaceDMA(false);patched=false;log('leave',0,0)end end,emu.callbackType.exec,0x7e2c07)
checkedMem527(function(a,v)
 base=a-0x520000;assert(base%16==0);words=0;consumed=0;readyAt=nil;nextFree=clock()+1;bad=false;advance(clock());log('prime',base,v)
end,emu.callbackType.write,0x520000,0x53ffff)
checkedMem527(function(a)
 advance(clock());local flags=(bad and 128 or 0)+(consumed==16 and 2 or 0)+(words-consumed//2==2 and 1 or 0)
 return flags
end,emu.callbackType.read,0x520000,0x53ffff)
checkedMem527(function(a)
 advance(clock());local off=a-0x500000
 local valid=off==base+consumed and words*2>consumed and consumed<16
 local b=valid and chr:byte(off+1) or 0
 if valid and not bad then consumed=consumed+1;nextFree=math.max(nextFree,clock()+1) else bad=true end
 log('read',off,b);return b
end,emu.callbackType.read,0x500000,0x51ffff)
checkedMem527(function()log('reject',base,bad and 1 or 0);local f=assert(io.open(ROOT..'/reject659.txt','w'));f:write(word(0x1226),' ',clock(),' ',words,' ',consumed);f:close();emu.stop()end,emu.callbackType.write,0x5f6000)
end
