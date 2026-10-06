
local cpu=assert(io.open(OUT_DIR..'/cpu-phase.tsv','w'))
local dumped=false
local function cpurow(kind,a,v)
 local s=emu.getState();local line=s['ppu.scanline'];local dot=s['ppu.cycle']
 if s.frameCount<6 or not ((line==62 and dot>=200) or (line==63 and dot<80)) then return end
 if not dumped then
  local f=assert(io.open(OUT_DIR..'/state-keys.txt','w'));local keys={}
  for k,v in pairs(s) do if string.find(k,'cpu') then keys[#keys+1]=k..'='..tostring(v) end end
  table.sort(keys);f:write(table.concat(keys,'\n'));f:close();dumped=true
 end
 cpu:write(table.concat({kind,s.frameCount,line,dot,s['ppu.masterClock'],s.masterClock,emu.read(1,emu.memType.nesInternalRam),a,v,s['cpu.pc'] or -1,s['cpu.irqFlag'] or -1},'\t')..'\n')
end
emu.addMemoryCallback(function(a,v)cpurow('R',a,v)end,emu.callbackType.read,0,0xffff,emu.cpuType.nes)
emu.addMemoryCallback(function(a,v)cpurow('W',a,v)end,emu.callbackType.write,0,0xffff,emu.cpuType.nes)
emu.addMemoryCallback(function(a,v)cpurow('X',a,v)end,emu.callbackType.exec,0,0xffff,emu.cpuType.nes)
-- SPDX-License-Identifier: MIT. Observational callbacks; no replacement values.
local trace=assert(io.open(OUT_DIR..'/trace.tsv','w'))
local frames=assert(io.open(OUT_DIR..'/frames.tsv','w'))
local function row(kind,a,v,p,t)
 local s=emu.getState()
 if kind=='read' and s.frameCount<6 then return end
 trace:write(table.concat({kind,s.frameCount,s['ppu.scanline'],s['ppu.cycle'],s['ppu.masterClock'],s.masterClock,a,v,p,t},'\t')..'\n')
end
emu.addMemoryCallback(function(a,v)
 local p=emu.convertAddress(a,emu.memType.nesPpuMemory,emu.cpuType.nes);row('read',a,v,p.address,p.memType)
end,emu.callbackType.read,0,0x1fff,emu.cpuType.nes,emu.memType.nesPpuMemory)
emu.addMemoryCallback(function(a,v)row('write',a,v,-1,-1)end,emu.callbackType.write,0x8000,0xffff,emu.cpuType.nes)
emu.addMemoryCallback(function(a,v)row('ram',a,v,-1,-1)end,emu.callbackType.write,0,7,emu.cpuType.nes)
emu.addMemoryCallback(function(a,v)
 local p=emu.convertAddress(a,emu.memType.nesMemory,emu.cpuType.nes);row('prg',a,v,p.address,p.memType)
end,emu.callbackType.read,0x8000,0x8000,emu.cpuType.nes)
emu.addEventCallback(function()
 local s=emu.getState()
 if s.frameCount>=6 then
  local size=emu.getScreenSize();local buf=emu.getScreenBuffer();local r={}
  for a=0,7 do r[#r+1]=emu.read(a,emu.memType.nesInternalRam)end
  frames:write(table.concat({s.frameCount,table.unpack(r)},'\t')..'\n');frames:flush()
  local f=assert(io.open(string.format('%s/frame-%03d.rgb',OUT_DIR,s.frameCount),'wb'))
  for y=0,239 do
   local row={};for x=0,255 do local c=buf[y*256+x+1];row[#row+1]=string.char((c>>16)&255,(c>>8)&255,c&255)end;f:write(table.concat(row))
  end
  f:close()
 end
 trace:flush()
 if s.frameCount==9 then trace:close();frames:close();cpu:close();emu.stop(0)end
end,emu.eventType.endFrame)
