local f=-118
local pages,writes={},0
local trace=assert(io.open(OUTPUT..'/walk.tsv','w'))
trace:write('frame\twrites\tpages\tmask\n')
emu.addMemoryCallback(function(a)
 local v=emu.convertAddress(a,m.nesPpuMemory,emu.cpuType.nes)
 assert(v.memType==m.nesChrRam)
 pages[v.address>>10]=true
 writes=writes+1
end,emu.callbackType.write,0,0x1fff,emu.cpuType.nes,m.nesPpuMemory)
emu.addEventCallback(function() emu.setInput({down=f>=15},0) end,emu.eventType.inputPolled)
emu.addEventCallback(function()
 f=f+1
 if f==2 then pending=true end
 if f>0 then
  local mask=0
  for page in pairs(pages) do mask=mask|(1<<page) end
  local state=emu.getState()
  local mode=(state['ppu.mask.grayscale'] and 1 or 0)+(state['ppu.mask.backgroundEnabled'] and 8 or 0)+(state['ppu.mask.spritesEnabled'] and 16 or 0)
  trace:write(string.format('%d\t%d\t%d\t%d\n',f,writes,mask,mode))
  if f==8 or f%30==0 or (f>=180 and f<=290 and f%4==0) then
   local pix=emu.getScreenBuffer()
   local file=assert(io.open(string.format('%s/%03d.ppm',OUTPUT,f),'wb'))
   file:write('P6\n256 240\n255\n')
   for y=0,239 do
    local line={}
    for x=0,255 do local c=pix[y*256+x+1];line[x+1]=string.char((c>>16)&255,(c>>8)&255,c&255) end
    file:write(table.concat(line))
   end
   file:close()
  end
 end
 writes=0;pages={}
 if f==900 then trace:close();emu.stop(0) end
end,emu.eventType.endFrame)
