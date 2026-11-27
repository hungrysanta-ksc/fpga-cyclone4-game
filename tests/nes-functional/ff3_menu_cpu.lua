-- Cartridge mailbox and pad are the boundary. CPU, PPU and VRAM are Mesen.
local panel=@LABELS@
local report=@REPORT@
local function finish(text,code)
 local f=assert(io.open(report,"w")); f:write(text); f:close(); emu.stop(code)
end
local function callback(fn,...)
 emu.addMemoryCallback(function(...)
  local ok,r=pcall(fn,...); if not ok then finish(tostring(r),1) end; return r
 end,...)
end
local mode=@MODE@
if mode=="turbo" then
 local samples,fields,last_field,low=0,0,-1,0
 local function held(i)
  if i<=120 then return 0x4040 end -- X and Y
  if i<=128 then return 0x0140 end -- right and X
  if i<=136 then return 0xc080 end -- held A/B with Y
  if i<=144 then return 0x4000 end -- Y alone
  return 0
 end
 emu.addEventCallback(function() fields=fields+1 end,emu.eventType.endFrame)
 callback(function(a) local v=held(samples+1);return a==0x4218 and v&255 or v>>8 end,
          emu.callbackType.read,0x4218,0x4219)
 callback(function(a) return 0 end,emu.callbackType.read,0x6000,0x6001)
 callback(function(a,v)
  if a==0x6002 then low=v;return end
  samples=samples+1
  local input=held(samples)
  local expected=input
  if (samples&2)==0 then expected=expected|((input&0x4040)<<1) end
  assert((low|(v<<8))==expected,"pad word "..samples)
  if samples>1 then assert(fields==last_field+1,"duplicate/skipped TV field") end
  last_field=fields
  if samples==148 then finish("PASS 148 fields; X/Y, held A/B, right and release",0) end
 end,emu.callbackType.write,0x6002,0x6003)
 return
end
local cmds={}
local sequence={0,0x400,0,0x80,0,0x400,0,0x80,0,0x400,0,0x80,0,0x400,0,0x80,0,0x8000}
if mode=="load" then
 sequence={0,0x400,0,0x400,0,0x80,0,0x400,0,0x400,0,0x80}
elseif mode=="exit" then
 sequence={0,0x800,0,0x80}
end
local buttons,step,status=0x1030,0,0
local video,palette=emu.memType.snesVideoRam,emu.memType.snesCgRam
local title_visible=false
emu.addEventCallback(function()
 if title_visible or step<1 or #cmds~=1 then return end
 local v=emu.getScreenSize()
 local pixels=emu.getScreenBuffer()
 local scale=v.width//256
 if scale<1 then return end
 local title=@TITLE@
 -- The visible NTSC field may include overscan. Locate the title by its
 -- complete seven scanlines, allowing the output filter to double samples.
 for top=0,math.min(64*scale,v.height-7*scale) do
  local ok=true
  for row=0,6 do
   for i,tile in ipairs(title) do
    local bits=emu.read(0xe000+16*tile+row*2,video)
    for x=0,7 do
     local rgb=pixels[(top+row*scale)*v.width+(32+(i-1)*8+x)*scale+1]&0xffffff
     if ((rgb&255)>128)~=(((bits>>(7-x))&1)==1) then ok=false;break end
    end
    if not ok then break end
   end
   if not ok then break end
  end
  if ok then title_visible=true;break end
 end
end,emu.eventType.endFrame)
local function checkbytes(seed)
 for _,r in ipairs({{video,0xe000,@FONT@},{video,0xf800,2048},{palette,0,2},{palette,130,2}}) do
  for n=r[2],r[2]+r[3]-1 do
   local expected=(n*13+7)&((r[1]==palette and n%2==1) and 127 or 255)
   if seed then emu.write(n,expected,r[1])
   else assert(emu.read(n,r[1])==expected,string.format("restore %x",n)) end
  end
 end
end
callback(function(a) return a==0x6002 and status or 0 end,emu.callbackType.read,0x6000,0x6005)
callback(function(a) return a==0x4218 and buttons&255 or buttons>>8 end,emu.callbackType.read,0x4218,0x4219)
callback(function(a,v)
 table.insert(cmds,v); status=(mode=="resume" and v==0x21) and 2 or 1
 if mode=="load" and v==0x21 then
  assert(table.concat(cmds,',')=="1,33")
  finish("PASS SLOT 2 LOAD STATE request after reset",0)
 elseif mode=="exit" and v==7 then
  assert(table.concat(cmds,',')=="1,7")
  finish("PASS EXIT TO MENU request",0)
 end
 if v==1 then checkbytes(true)
 elseif v==5 then
  assert(table.concat(cmds,',')=="1,2,17,33,5",table.concat(cmds,','))
  assert(title_visible,"rendered title pixels missing");checkbytes(false);buttons=0
 end
end,emu.callbackType.write,0x7002)
callback(function()
 if step==0 then
  local title=@TITLE@
  for i=1,#title do
   assert(emu.read(2*(0x7c00+100+i-1),video)==title[i],"title "..i)
  end
 end
 step=step+1; buttons=assert(sequence[step],"unexpected input loop")
end,emu.callbackType.exec,panel.input)
callback(function()
 if #cmds==5 then finish("PASS boot, chord, visible title, WRITE SRAM, SLOT 2, SAVE, missing LOAD, resume and exact VRAM/CGRAM",0) end
end,emu.callbackType.exec,panel.ordinary)
