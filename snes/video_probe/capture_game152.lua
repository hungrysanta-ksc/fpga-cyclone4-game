-- SPDX-License-Identifier: MIT
local f=assert(io.open(PAYLOAD,'rb'));local payload=f:read('*a');f:close()
assert(#payload==114688)
local page,reads,commits,shown=1,0,0,-1
local nextready,blanked=0,true
local log=assert(io.open(OUT_DIR..'/trace.tsv','w'))
emu.addMemoryCallback(function(a,v)
 return (page<=2 and emu.getState().frameCount>=nextready) and 1 or 0
end,emu.callbackType.read,0x6000,0x6000)
emu.addMemoryCallback(function(a,v)
 assert(page<=2 and reads<57344)
 assert((a&0xffff)==((0x8000+reads)&0xffff))
 assert(blanked,'visible VRAM upload')
 local value=payload:byte((page-1)*57344+reads+1);reads=reads+1
 return value
end,emu.callbackType.read,0x400000,0x40ffff)
emu.addMemoryCallback(function(a,v)
 if a==0x2100 then blanked=(v&128)~=0 end
 if a==0x7000 or a==0x2100 then
  local s=emu.getState();log:write(table.concat({a,v,s.masterClock,s.frameCount,s['ppu.scanline']},'\t')..'\n')
 end
 if a==0x7000 and v==6 then shown=emu.getState().frameCount end
 if a==0x6000 then
  assert(v==0xa5 and reads==57344 and not blanked)
  commits=commits+1;page=page+1;reads=0;nextready=emu.getState().frameCount+3
 end
end,emu.callbackType.write,0,0xffff)
local inputs=assert(io.open(OUT_DIR..'/inputs.tsv','w'))
local last_low=0
local function buttons(frame)
 local pulses={[10]=0x1000,[14]=0x0080,[18]=0x8000,[22]=0x0100,
               [26]=0x0200,[30]=0x0400,[34]=0x0800,[42]=0x2000,[46]=0x0800}
 return pulses[frame] or 0
end
emu.addMemoryCallback(function(a,v)
 local b=buttons(emu.getState().frameCount)
 return a==0x4218 and (b&255) or ((b>>8)&255)
end,emu.callbackType.read,0x4218,0x4219)
emu.addMemoryCallback(function(a,v)
 if a==0x6002 then last_low=v else
  local s=emu.getState();local b=(v<<8)|last_low
  assert(b==buttons(s.frameCount),'torn controller bytes')
  inputs:write(table.concat({s.frameCount,s.masterClock,b},'\t')..'\n')
 end
end,emu.callbackType.write,0x6002,0x6003)
local captured=0
emu.addEventCallback(function()
 local s=emu.getState()
 if commits>captured and s.frameCount>shown and not blanked then
  local size=emu.getScreenSize();local buf=emu.getScreenBuffer()
  local image=assert(io.open(OUT_DIR..'/frame-'..commits..'.rgb','wb'))
  for y=0,size.height-1 do local row={}
   for x=0,size.width-1 do local c=buf[y*size.width+x+1];row[#row+1]=string.char((c>>16)&255,(c>>8)&255,c&255)end
   image:write(table.concat(row))
  end
  image:close();captured=commits
  local m=assert(io.open(OUT_DIR..'/size.txt','w'));m:write(size.width..' '..size.height);m:close()
  if captured==2 then inputs:close();log:close();emu.stop(0)end
 end
 if s.frameCount>120 then error('game150 client watchdog')end
end,emu.eventType.endFrame)
