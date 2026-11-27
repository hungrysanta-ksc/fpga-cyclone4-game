local f=-118
local pages,writes={},0
local trace=assert(io.open(OUTPUT..'/walk.tsv','w'))
local history=assert(io.open(OUTPUT..'/chr-tiles.tsv','w'))
history:write('frame\ttouched_tiles\tchanged_tiles\n')
local last,touched={},{}
trace:write('frame\twrites\tpages\tmask\n')
emu.addMemoryCallback(function(a)
 local v=emu.convertAddress(a,m.nesPpuMemory,emu.cpuType.nes)
 assert(v.memType==m.nesChrRam)
 pages[v.address>>10]=true
 touched[v.address>>4]=true
 writes=writes+1
end,emu.callbackType.write,0,0x1fff,emu.cpuType.nes,m.nesPpuMemory)
emu.addEventCallback(function() emu.setInput({down=f>=15},0) end,emu.eventType.inputPolled)
emu.addEventCallback(function()
 f=f+1
 if f==2 then pending=true end
 if f>0 then
  if f==1 or f==3 then
   for a=0,8191 do last[a]=emu.read(a,m.nesChrRam) end
  end
  local written,changed={},{}
  for tile in pairs(touched) do
   table.insert(written,tile)
   local diff=false
   for a=16*tile,16*tile+15 do
    local v=emu.read(a,m.nesChrRam)
    if last[a]~=v then diff=true end
    last[a]=v
   end
   if diff then table.insert(changed,tile) end
  end
  table.sort(written);table.sort(changed)
  history:write(f,'\t',table.concat(written,','),'\t',table.concat(changed,','),'\n')
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
 writes=0;pages={};touched={}
 if f==900 then history:close() end
 if f==900 then trace:close();emu.stop(0) end
end,emu.eventType.endFrame)
