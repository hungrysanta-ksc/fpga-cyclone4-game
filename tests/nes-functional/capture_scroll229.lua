-- SPDX-License-Identifier: MIT. Inputs only; never replace memory callback values.
local frames=assert(io.open(OUT_DIR..'/frames.tsv','w'))
local captureFrame=0
local fetches=assert(io.open(OUT_DIR..'/ppu-fetch.bin','wb'))
local writes=assert(io.open(OUT_DIR..'/writes.bin','wb'))
local chunks={}
local function enabled() return CAP_FIRST>0 and captureFrame>=CAP_FIRST and captureFrame<=CAP_LAST end
local function byte(v) return v and 1 or 0 end
local function mode(s)
 local mask=byte(s['ppu.mask.grayscale'])+2*byte(s['ppu.mask.backgroundMask'])+4*byte(s['ppu.mask.spriteMask'])+
  8*byte(s['ppu.mask.backgroundEnabled'])+16*byte(s['ppu.mask.spritesEnabled'])+s['ppu.intensifyColorBits']
 local ctrl=(s['ppu.control.backgroundPatternAddr']//4096)*16+(s['ppu.control.spritePatternAddr']//4096)*8+32*byte(s['ppu.control.largeSprites'])
 return mask,ctrl
end
emu.addEventCallback(function() captureFrame=emu.getState().frameCount end,emu.eventType.startFrame)
if CAP_FIRST>0 then
 emu.addMemoryCallback(function(a,v)
  if not enabled() then return end
  local s=emu.getState();local p=emu.convertAddress(a,emu.memType.nesPpuMemory,emu.cpuType.nes)
  local mask,ctrl=mode(s)
  local rank=math.max(0,math.min(7,(s['ppu.cycle']-257)//8))*4
  chunks[#chunks+1]=string.pack('<I4i2I2I2BI4I2I2I2BBBBBBB',s.frameCount,s['ppu.scanline'],s['ppu.cycle'],a,v,
   p.address,p.memType,s['ppu.videoRamAddr'],s['ppu.tmpVideoRamAddr'],s['ppu.xScroll'],mask,ctrl,
   s['ppu.secondarySpriteRam'..rank],s['ppu.secondarySpriteRam'..(rank+1)],
   s['ppu.secondarySpriteRam'..(rank+2)],s['ppu.secondarySpriteRam'..(rank+3)])
 end,emu.callbackType.read,0,0x1fff,emu.cpuType.nes,emu.memType.nesPpuMemory)
 local function write(kind,a,v)
  if not enabled() then return end
  local s=emu.getState()
  writes:write(string.pack('<BI4i2I2I2B',kind,s.frameCount,s['ppu.scanline'],s['ppu.cycle'],a,v))
 end
 emu.addMemoryCallback(function(a,v) write(0,a,v) end,emu.callbackType.write,0x2000,0x2007,emu.cpuType.nes)
 emu.addMemoryCallback(function(a,v) write(1,a,v) end,emu.callbackType.write,0x8000,0xffff,emu.cpuType.nes)
 emu.addMemoryCallback(function(a,v) write(2,a,v) end,emu.callbackType.write,0x0000,0x3fff,emu.cpuType.nes,emu.memType.nesPpuMemory)
 emu.addMemoryCallback(function(a,v) write(3,a,v) end,emu.callbackType.write,0x4014,0x4014,emu.cpuType.nes)
end
local function input(f)
 local p={a=false,b=false,select=false,start=false,up=false,down=false,left=false,right=false}
 if (f>=120 and f<124) or (f>=240 and f<244) then p.start=true end
 if f>=600 and f<620 then p.right=true end
 if f>=630 and f<650 then p.up=true end
 if f>=690 and f<694 then p.a=true end
 if f>=840 then p.right=true;p.b=true;p.a=(f%60)<36 end
 return p
end
emu.addEventCallback(function()
 local f=emu.getState().frameCount
 emu.setInput(input(f),0)
end,emu.eventType.inputPolled)
local function screenshot(f)
 local size=emu.getScreenSize();local buf=emu.getScreenBuffer()
 assert(size.width==256 and size.height==240)
 local file=assert(io.open(string.format('%s/frame-%04d.rgb',OUT_DIR,f),'wb'))
 for y=0,239 do
  local row={}
  for x=0,255 do local c=buf[y*256+x+1];row[#row+1]=string.char((c>>16)&255,(c>>8)&255,c&255) end
  file:write(table.concat(row))
 end
 file:close()
end
emu.addEventCallback(function()
 local s=emu.getState();local f=s.frameCount
 if #chunks>0 then fetches:write(table.concat(chunks));chunks={} end
 if CAP_FIRST>0 and f>=CAP_FIRST-1 and f<=CAP_LAST then
  local file=assert(io.open(string.format('%s/state-%04d.bin',OUT_DIR,f),'wb'))
  for _,part in ipairs({{emu.memType.nesNametableRam,2048},{emu.memType.nesSpriteRam,256},{emu.memType.nesPaletteRam,32}}) do
   local row={};for a=0,part[2]-1 do row[#row+1]=string.char(emu.read(a,part[1])) end;file:write(table.concat(row))
  end
  for a=0,7 do local p=emu.convertAddress(a*1024,emu.memType.nesPpuMemory,emu.cpuType.nes);file:write(string.pack('<I4I2',p.address,p.memType)) end
  file:close()
 end
 if f==1 then
  local file=assert(io.open(OUT_DIR..'/state-fields.txt','w'))
  for k,v in pairs(s) do file:write(tostring(k)..'\t'..tostring(v)..'\n') end
  for k,v in pairs(emu.memType) do file:write('memType.'..k..'\t'..tostring(v)..'\n') end
  for k,v in pairs(emu.getInput(0)) do file:write('input.'..k..'\t'..tostring(v)..'\n') end
  file:close()
 end
 local p=input(f)
 frames:write(table.concat({f,s.masterClock,p.start and 1 or 0,p.right and 1 or 0,p.b and 1 or 0,p.a and 1 or 0},'\t')..'\n')
 if f%30==0 or (CAP_FIRST>0 and f>=CAP_FIRST and f<=CAP_LAST) then screenshot(f);frames:flush() end
 if f>=END_FRAME then frames:close();fetches:close();writes:close();emu.stop(0) end
end,emu.eventType.endFrame)
