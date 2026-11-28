local out=assert(io.open(@OUT@,"w"))
local writes={}
local bus=assert(io.open(@BUS@,"w"))
local frames=0
emu.addMemoryCallback(function(a,v)
 local entry=writes[a] or {0,frames,v}
 entry[1]=entry[1]+1
 writes[a]=entry
 if a>=0x8000 or (a>=0x5000 and a<0x6000) then
  bus:write(string.format("0 %04x %02x\n",a,v))
 end
end,emu.callbackType.write,0x5000,0xffff)
emu.addEventCallback(function()
 frames=frames+1
 if frames%120==0 then
  for a=0x8000,0xe000,0x2000 do
   local p=emu.convertAddress(a,emu.memType.nesMemory,emu.cpuType.nes)
   if p and p.memType==emu.memType.nesPrgRom then bus:write(string.format("1 %04x %x\n",a,p.address)) end
  end
  for a=0,0x1c00,1024 do
   local p=emu.convertAddress(a,emu.memType.nesPpuMemory,emu.cpuType.nes)
   assert(p and (p.memType==emu.memType.nesChrRom or p.memType==emu.memType.nesChrRam))
   bus:write(string.format("2 %04x %x\n",a,p.address))
  end
  for a=0x2000,0x2c00,1024 do
   local p=emu.convertAddress(a,emu.memType.nesPpuMemory,emu.cpuType.nes)
   assert(p)
   bus:write(string.format("3 %04x %x\n",a,p.address & 2047))
  end
  local screen=emu.getScreenBuffer()
  local colors={}
  local digest=0
  for _,v in ipairs(screen) do colors[v]=true;digest=((digest*31)~v)&0xffffffff end
  local n=0;for _ in pairs(colors) do n=n+1 end
  out:write(string.format("FRAME %d %d %08x\n",frames,n,digest))
 end
 if frames==1800 then
  for a=0x5000,0xffff do
   local e=writes[a]
   if e then out:write(string.format("%04x %d %d %02x\n",a,e[1],e[2],e[3])) end
  end
  out:write("END 1800\n");out:close();bus:close();emu.stop(0)
 end
end,emu.eventType.endFrame)
