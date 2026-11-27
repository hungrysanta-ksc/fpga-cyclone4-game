-- Test driver around the verified WRAM client. CPU, DMA and VRAM are Mesen.
local dir,raw,fill=@ROOT@,@RAW@,@FILL@
local f=assert(io.open(dir.."/cases","rb"));local data=f:read("*a");f:close()
local wr,vr=emu.memType.snesWorkRam,emu.memType.snesVideoRam
local function put(a,v) emu.write(a,v&255,wr) end
local function word(a,v) put(a,v);put(a+1,v>>8) end
local function done(s,n) local o=assert(io.open(dir.."/result","w"));o:write(s);o:close();emu.stop(n) end
local function hook(addr,fn)
 emu.addMemoryCallback(function() local ok,msg=pcall(fn);if not ok then done(tostring(msg),1) end end,emu.callbackType.exec,addr)
end
-- A16/X16, DBR=0, forced blank. The service reads the ordinary STOP port.
local code={0xc2,0x30,0xad,0x00,0x08,0x20,raw&255,raw>>8,0x4c,0x00,0x1a}
emu.addMemoryCallback(function() return 0 end,emu.callbackType.read,0x6000,0x6001)
hook(0x00a000,function()
 for i,b in ipairs(code) do put(0x1a00+i-1,b) end
end)
local pos,bank,total,wrong=1,0,0,0
local pixels,count,dest
hook(0x7e1a00,function()
 if pos>#data then done("PASS "..total.." "..wrong,0);return end
 count=data:byte(pos);pixels=data:sub(pos+1,pos+256*count)
 dest=bank==0 and 0x5000 or 0x9000
 for i=0,2047 do emu.write(dest+i,0,vr) end
 word(0x800,dest);word(0x1020,0);word(0x1236,0);word(0x1240,count)
 word(0x125c,2);word(0x78,0)
 local at=0x16961
 for pair=0,2 do for r=0,count-1 do for tile=0,31 do for bit=0,1 do
  local v=0
  for x=0,7 do v=(v<<1)|((pixels:byte(1+r*256+tile*8+x)>>(2*pair+bit))&1) end
  put(at,v);at=at+1
 end end end end
end)
hook(0x7e1a08,function()
 for r=0,count-1 do for x=0,255 do
  local got=0
  for bit=0,7 do
   local v=emu.read(dest+(x//8)*64+(bit//2)*16+2*r+bit%2,vr)
   got=got|(((v>>(7-x%8))&1)<<bit)
  end
  local original=pixels:byte(1+r*256+x)
  assert(got==(original|(((fill>>(7-x%8))&1)<<6)),"unexpected DMA pixel "..x.." "..got)
  total=total+1;if got~=64+original then wrong=wrong+1 end
 end end
 if bank==1 then pos=pos+1+count*256 end;bank=1-bank
end)
