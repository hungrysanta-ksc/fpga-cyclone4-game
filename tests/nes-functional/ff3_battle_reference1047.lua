local src=assert(io.open(ROOT.."/slot.bin","rb")):read("*a")
local tr=assert(io.open(ROOT.."/frames.txt","w"))
local colors=assert(io.open(ROOT.."/flash.hex","w"))
local m=emu.memType
local function wd(i) return string.unpack("<i8",src,i*8+1) end
local function bits(i,sh,mask) return (wd(i)>>sh)&mask end
local function init()
 for _,v in ipairs({{m.nesInternalRam,11024,2048},{m.nesSaveRam,13072,8192},{m.nesChrRam,784,8192},{m.nesNametableRam,8976,2048},{m.nesSpriteRam,520,256}}) do
  for a=0,v[3]-1 do emu.write(a,src:byte(1+v[2]+a),v[1]) end
 end
 for i=0,31 do emu.write(i,src:byte(65+(i%4)*8+(i//4)),m.nesPaletteRam) end
 local banks={2*bits(33,39,255),2*bits(33,47,255),bits(33,55,255),bits(34,0,255),bits(34,8,255),bits(34,16,255),bits(34,24,63),bits(34,30,63)}
 local mode=bits(33,10,3)*64
 for i,a in ipairs(banks) do emu.write(0x8000,mode+i-1,m.nesMemory);emu.write(0x8001,a,m.nesMemory) end
 emu.write(0x8000,mode+bits(33,7,7),m.nesMemory)
 emu.write(0xa000,bits(33,12,1),m.nesMemory);emu.write(0xa001,0x80,m.nesMemory)
 emu.write(0x2000,0x80+bits(5,2,1)*16+bits(5,1,1)*8+bits(5,3,1)*32,m.nesMemory)
 emu.write(0x2001,0x1e,m.nesMemory)
 -- A fresh reference APU otherwise asserts an extra frame IRQ in the battle menu.
 emu.write(0x4017,bits(20,19,3)*64,m.nesMemory)
 emu.write(0xc000,bits(33,15,255),m.nesMemory)
 emu.write(bits(33,13,1)==1 and 0xe001 or 0xe000,0,m.nesMemory)
 local s=emu.getState()
 s["apu.frameCounter.inhibitIRQ"]=bits(20,19,1)==1
 s["apu.frameCounter.irqFlag"]=bits(20,15,1)==1
 s["apu.frameCounter.newValue"]=bits(20,19,3)*64
 s["apu.frameCounter.writeDelayCounter"]=1
 s["mapper.irqCounter"]=bits(33,23,255)
 s["mapper.irqReload"]=bits(33,14,1)==1
 s["ppu.videoRamAddr"]=bits(12,1,32767)
 s["ppu.tmpVideoRamAddr"]=bits(12,16,32767)
 s["ppu.writeToggle"]=bits(12,34,1)==1
 -- These two physical snapshots stop inside an idempotent JMP abs / LDA zp.
 -- Mesen sets PC at an instruction boundary; replay the interrupted opcode.
 local pc=bits(1,0,65535)-2
 assert((BATTLE and pc==0xfb82 and bits(1,16,255)==0xa5) or
        (not BATTLE and pc==0xff45 and bits(1,16,255)==0x4c))
 assert(emu.read(pc,m.nesMemory)==bits(1,16,255))
 s['cpu.pc']=pc;s['cpu.sp']=bits(1,24,255)
 s['cpu.ps']=bits(2,2,255);s['cpu.a']=bits(2,10,255);s['cpu.x']=bits(2,18,255);s['cpu.y']=bits(2,26,255)
 emu.setState(s)
end

local pending=false
-- End-of-frame can interrupt the middle of the reset program's self-jump.
-- Apply the state at the next opcode fetch and return that checkpoint opcode.
emu.addMemoryCallback(function()
 if pending then pending=false;init();return bits(1,16,255) end
end,emu.callbackType.exec,0xff45,0xff45)
local f=-118; local masks={};local wr=0;local chrwr=0;local minchr=8192;local maxchr=0;local lastbuf={}
emu.addMemoryCallback(function(addr,val) masks[val]=(masks[val] or 0)+1 end,emu.callbackType.write,0x2001,0x2001)
emu.addMemoryCallback(function(addr,val) wr=wr+1 end,emu.callbackType.write,0x2007,0x2007)
emu.addMemoryCallback(function(addr,val) chrwr=chrwr+1;minchr=math.min(minchr,addr);maxchr=math.max(maxchr,addr) end,emu.callbackType.write,0,0x1fff,emu.cpuType.nes,m.nesPpuMemory)
-- Read-only evidence around the first visible attack effect. Resolve each
-- logical CHR page again if the game changes a mapper register in that field.
local physical=assert(io.open(ROOT.."/attack-patterns.bin","wb"))
local pages,used={},{}
local function fetched(addr)
 if not (BATTLE and f>=508 and f<574) then return end
 local page=addr>>10
 if pages[page]==nil then
  local mapped=emu.convertAddress(addr,m.nesPpuMemory,emu.cpuType.nes)
  assert(mapped.memType==m.nesChrRam and mapped.address>=0 and mapped.address<8192)
  pages[page]=mapped.address>>10
 end
 used[(pages[page]<<6)|((addr>>4)&63)]=true
end
if BATTLE then
 emu.addMemoryCallback(fetched,emu.callbackType.read,0,0x1fff,emu.cpuType.nes,m.nesPpuMemory)
 emu.addMemoryCallback(function() pages={} end,emu.callbackType.write,0x8000,0x9fff,emu.cpuType.nes)
end
emu.addEventCallback(function()
 local t=f%128
 if BATTLE then emu.setInput({a=(f%10)<3},0)
 else emu.setInput({down=f<65 or (f>=65 and t>=64),up=f>=65 and t<64},0) end
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
 f=f+1;if f<1 then return end;if f==2 then pending=true end
 local pix=emu.getScreenBuffer();local hist={};local peak=0;local dom=0;local dif=0
 for y=8,231,2 do for x=0,255,2 do local i=y*256+x+1;local c=pix[i];local n=(hist[c] or 0)+1;hist[c]=n;if n>peak then peak=n;dom=c end;if lastbuf[i]~=c then dif=dif+1 end end end
 if BATTLE and f>=509 and f<=574 then
  local bitmap,ram={},{}
  for i=0,511 do bitmap[i+1]=used[i] and "1" or "0" end
  for i=0,8191 do ram[i+1]=string.char(emu.read(i,m.nesChrRam)) end
  physical:write(table.concat(bitmap),table.concat(ram))
 end
 pages={};used={}
 lastbuf=pix;local cols=0;for _ in pairs(hist) do cols=cols+1 end
 local labels={};for k,v in pairs(masks) do table.insert(labels,string.format("%02x:%d",k,v)) end;table.sort(labels)
 tr:write(string.format("%d %d %06x %d %d %d %d %x %x %s",f,cols,dom&0xffffff,peak,dif,wr,chrwr,minchr,maxchr,table.concat(labels,",")),"\n");tr:flush()
 if not BATTLE then
  local mask=next(masks)
  if not mask or next(masks,mask) then mask=255 end
  colors:write(string.format("%02x ",mask))
  for i=0,31 do colors:write(string.format("%02x ",emu.read(i,m.nesPaletteRam)&63)) end
  colors:write("\n")
 end
 masks={}; wr=0;chrwr=0;minchr=8192;maxchr=0
 if f==LIMIT then physical:close();colors:close();tr:close();emu.stop(0) end
end,emu.eventType.endFrame)
