-- SPDX-License-Identifier: MIT
local failed=nil
local function check(value,message)
 if not value then
  if failed then error(failed)end
  failed=message or 'assertion failed'
  local f=io.open(OUT_DIR..'/failure.txt','w');f:write(message or 'assertion failed');f:close()
  error(message or 'assertion failed')
 end
 return value
end
local assert=check
local f=assert(io.open(PAYLOAD,'rb'));local payload=f:read('*a');f:close()
assert(#payload==114688)
local page,reads,commits,captured=1,0,0,0
local nextready,blanked,revealed,doneframe=0,true,false,-1
local status=nil
local trace=assert(io.open(OUT_DIR..'/trace.tsv','w'))
local inputs=assert(io.open(OUT_DIR..'/inputs.tsv','w'))
local dmas=assert(io.open(OUT_DIR..'/dma.tsv','w'))
local count,port,remaining,chunk,chunkframe=0,0,0,0,-1
local first_visible_frame=nil
local padframes={}
local function timing()
 local s=emu.getState();return s.frameCount,s['ppu.scanline'],s.masterClock
end
emu.addMemoryCallback(function(a,v)
 return page<=2 and emu.getState().frameCount>=nextready and 1 or 0
end,emu.callbackType.read,0x6000,0x6000)
emu.addMemoryCallback(function(a,v)
 local frame,line,tick=timing()
 assert(page<=2 and reads<57344 and remaining>0,'unexpected source read')
 assert((a&0xffff)==((0x8000+reads)&0xffff),'source address/wrap')
 if page>1 then assert(not blanked and line>=225 and frame==chunkframe,'DMA escaped vblank')end
 local value=payload:byte((page-1)*57344+reads+1)
 reads=reads+1;remaining=remaining-1
 if remaining==0 then dmas:write(table.concat({page,chunk,count,chunkframe,frame,line,tick},'\t')..'\n');dmas:flush()end
 return value
end,emu.callbackType.read,0x400000,0x40ffff)
emu.addMemoryCallback(function(a,v)
 local frame,line,tick=timing()
 if a==0x2100 then
  blanked=(v&128)~=0
  if revealed then assert(not blanked,'display blanked after initial reveal')end
  if not blanked then revealed=true;first_visible_frame=first_visible_frame or frame end
 end
 if (a==0x2118 or a==0x2119) and revealed then assert(line>=225,'visible VRAM write')end
 if a==0x4301 then port=v end
 if a==0x4305 then count=(count&0xff00)|v end
 if a==0x4306 then count=(count&0xff)|(v<<8) end
 if a==0x420b and port==0x18 then
  assert(v==1 and remaining==0);remaining=count;chunk=chunk+1;chunkframe=frame
  if page>1 then assert(not blanked and line>=225)end
 end
 if a==0x7001 then assert(status==nil);status=v;assert(status==0xa9,'SPC initialization regressed')end
 if a==0x7000 or a==0x2100 then trace:write(table.concat({a,v,tick,frame,line},'\t')..'\n')end
 if a==0x6000 then
  assert(v==0xa5 and reads==57344 and remaining==0 and not blanked,'early snapshot release')
  assert(chunk==(page==1 and 1 or 11),'chunk count')
  commits=commits+1;page=page+1;reads=0;chunk=0;doneframe=frame;nextready=frame+READY_DELAY
 end
end,emu.callbackType.write,0,0xffff)
local lastlow=0
local function buttons(frame)
 -- Include a sustained DOWN interval, then changing masks and release.
 if frame>=8 and frame<=20 then return 0x0400 end
 local masks={0,0x0080,0x8000,0x0100,0x0200,0x0400,0x2000,0x0800}
 return masks[(frame%8)+1]
end
emu.addMemoryCallback(function(a,v)
 local b=buttons(emu.getState().frameCount);return a==0x4218 and (b&255) or ((b>>8)&255)
end,emu.callbackType.read,0x4218,0x4219)
emu.addMemoryCallback(function(a,v)
 if a==0x6002 then lastlow=v else
  local frame,line,tick=timing();local b=(v<<8)|lastlow
  assert(b==buttons(frame),'torn controller pair');padframes[frame]=true
  inputs:write(table.concat({frame,tick,b,line},'\t')..'\n')
 end
end,emu.callbackType.write,0x6002,0x6003)
emu.addEventCallback(function()
 if failed then emu.stop(1);return end
 local s=emu.getState()
 if commits>captured and s.frameCount>doneframe and not blanked then
  local size=emu.getScreenSize();local buf=emu.getScreenBuffer()
  -- Mesen returns a239-line canvas including the224-line active picture.
  assert(size.width==256 and size.height==239,'screen size '..size.width..'x'..size.height)
  local image=assert(io.open(OUT_DIR..'/frame-'..commits..'.rgb','wb'))
  for y=0,size.height-1 do local row={}
   for x=0,size.width-1 do local c=buf[y*size.width+x+1];row[#row+1]=string.char((c>>16)&255,(c>>8)&255,c&255)end
   image:write(table.concat(row))
  end
  image:close();captured=commits
  if captured==2 then
   assert(status==0xa9)
   for frame=first_visible_frame+1,doneframe do assert(padframes[frame],'pad polling gap at '..frame)end
   inputs:close();trace:close();dmas:close();emu.stop(0)
  end
 end
 if s.frameCount>150 then error('game164 client watchdog')end
end,emu.eventType.endFrame)
