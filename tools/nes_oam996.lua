local out996=assert(io.open(ROOT..'/oam996.csv','w'))
out996:write('event,g,op,offset,address,value,clock,pc\n')
local base996,port996,active996=0,0,false
local function log996(kind,address,value)
 local st=emu.getState()
 out996:write(string.format('%s,%d,%d,%d,%d,%d,%d,%d\n',kind,packet and pw(8) or -1,
  packet and pb(0) or -1,packet and pw(10) or -1,address,value,st.masterClock,st['cpu.pc'] or 0))
end
local function snap996(kind)
 for i=176,543 do log996(kind,i,rd(base996+i)) end
 out996:flush()
end
-- Track the SNES WRAM data port even while the other bank is owned.
checkedMem527(function(a,v)
 if a==0x2181 then port996=(port996&0x1ff00)|v
 elseif a==0x2182 then port996=(port996&0x100ff)|(v<<8)
 elseif a==0x2183 then port996=(port996&0xffff)|((v&1)<<16)
 else
  if active996 and port996>=base996+176 and port996<base996+544 then log996('port',port996-base996,v) end
  port996=(port996+1)&0x1ffff
 end
end,emu.callbackType.write,0x2180,0x2183)
checkedMem527(function()port996=(port996+1)&0x1ffff end,emu.callbackType.read,0x2180)
checkedMem527(function(a,v)
 local n=(a&0x1ffff)-base996
 if active996 and n>=176 and n<544 then log996('direct',n,v) end
end,emu.callbackType.write,0x7f6200,0x7fffff)
