local out=assert(io.open(OUTPUT,"w"))
local frame,control=0,0
emu.addMemoryCallback(function(_,value) control=value end,emu.callbackType.write,0x2000,0x2000)
emu.addEventCallback(function()
 emu.setInput({start=frame>=150 and frame<5800 and frame%90<8,
               a=frame>=180 and frame%40<8,right=frame>=5800},0)
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
 if (frame>=2100 and frame<2160) or (frame>=6000 and frame<6060) then
  local oam={}
  for i=0,255 do oam[#oam+1]=string.format("%02x",emu.read(i,emu.memType.nesSpriteRam)) end
  out:write(frame," ",control," ",table.concat(oam),"\n")
 end
 frame=frame+1
 if frame==6061 then out:close();emu.stop(0) end
end,emu.eventType.endFrame)
