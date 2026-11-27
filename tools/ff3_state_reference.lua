-- Mesen reference only. Use a private save folder and a copy of the ROM.
local frame, checkpoint, rep, pending = 0, nil, 1, nil
local seen = {}
local m = emu.memType
local log = assert(io.open(OUT, "w"))
local function check(ok, message)
  if not ok then log:write(message,"\n"); log:flush(); emu.stop(1); error(message) end
end
local function fingerprint()
  local screen = emu.getScreenBuffer()
  local h = 2166136261
  for i=1,#screen do h = ((h ~ screen[i]) * 16777619) & 0xffffffff end
  local values = {h}
  for _,mem in ipairs({m.nesChrRam, m.nesSaveRam, m.nesInternalRam, m.nesSpriteRam, m.nesPaletteRam}) do
    local x=2166136261
    for i=0,emu.getMemorySize(mem)-1 do x=((x ~ emu.read(i,mem))*16777619) & 0xffffffff end
    values[#values+1]=x
  end
  return table.concat(values,",")
end
local handle
local chr_previous={}
local chr_peak,chr_dirty_frames,chr_dirty_total=0,0,0
local function count_chr_changes()
  local dirty=0
  for tile=0,511 do
    local changed=false
    for p=tile*16,tile*16+15 do
      local value=emu.read(p,m.nesChrRam)
      if chr_previous[p]~=nil and chr_previous[p]~=value then changed=true end
      chr_previous[p]=value
    end
    if changed then dirty=dirty+1 end
  end
  if dirty>0 then chr_dirty_frames=chr_dirty_frames+1 end
  chr_peak=math.max(chr_peak,dirty)
  chr_dirty_total=chr_dirty_total+dirty
end
local function exec()
  emu.removeMemoryCallback(handle,emu.callbackType.exec,0x8000,0xffff)
  if rep==1 then
    checkpoint=emu.createSavestate()
    check(type(checkpoint)=="string" and #checkpoint>0,"empty reference state")
  else
    check(emu.loadSavestate(checkpoint),"reference restore failed")
  end
  pending=false
end
for _,k in ipairs({"nesPrgRom","nesChrRam","nesSaveRam","nesChrRom"}) do
  log:write(k,"=",emu.getMemorySize(m[k]),"\n")
end
log:flush()
emu.addEventCallback(function()
  frame=frame+1
  if rep==1 and frame<=600 then count_chr_changes() end
  if frame==600 then
    pending=true
    handle=emu.addMemoryCallback(exec,emu.callbackType.exec,0x8000,0xffff)
  elseif frame>600 and frame<=660 then
    check(not pending,"no CPU checkpoint")
    local value=fingerprint()
    if rep==1 then seen[frame]=value else check(value==seen[frame],"replay mismatch at "..frame) end
    if frame==660 then
      if rep==1 then rep=2; frame=599
      else
        log:write("matched_frames=60\nchr_sample_frames=600\nchr_changed_frames=",chr_dirty_frames,
                  "\nchr_tile_frame_changes=",chr_dirty_total,"\nchr_max_changed_tiles=",chr_peak,"\n")
        log:close();emu.stop(0)
      end
    end
  end
end,emu.eventType.endFrame)

