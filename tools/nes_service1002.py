"""Count receiver service up to packet return or SEAL-to-upload on the 978 CPU."""
from nes_dma1000 import ORIGIN, PACKED, once


def instrument(lua):
    # Use the shortest legal instruction width, including 8-bit immediates.
    widths = {}
    for size, codes in ((2,"29 49 64 65 69 80 85 89 90 a0 a2 a5 a9 b0 b7 c0 c2 c5 c9 d0 e0 e2 e9 f0"),
                        (3,"19 20 4c 6d 8d 9c 9d ac ad ae bd cd dd"),(4,"af bf")):
        widths.update({int(v,16):size for v in codes.split()})
    sizes = "".join(str(widths.get(b,1)) for b in (PACKED/"body.bin").read_bytes())
    pos = "local function sample516(event,value)"
    lua = once(lua,pos,"""local size1002='SIZES'
local work1002=assert(io.open(ROOT..'/cycles1002.csv','w'))
work1002:write('op,sec,offset,token,cycles,minfetch,clockspan,signature\\n')
local track1002=false
local hooked1002=false
local cycles1002,tick1002,fetch1002,hash1002=0,0,0,0
""".replace("SIZES",sizes)+pos+"""
 if packet and pw(8)==912 then
  if event=='load' then
   if not hooked1002 then
    hooked1002=true
    checkedMem527(function(pc)
     if track1002 then
      fetch1002=fetch1002+size1002:byte(pc-ORIGIN+1)-48
      hash1002=((hash1002*31)+pc)&0xffffffff
     end
    end,emu.callbackType.exec,ORIGIN,ORIGIN+#size1002-1)
   end
   local st=emu.getState();track1002=true
   cycles1002=st['cpu.cycleCount'];tick1002=st.masterClock;fetch1002=0;hash1002=0
  elseif track1002 and (event=='ack' or event=='upload165_entry') then
   track1002=false
   local st=emu.getState()
   work1002:write(string.format('%d,%d,%d,%d,%d,%d,%d,%d\\n',pb(0),pb(1),pw(10),
       pb(0)==7 and pw(16) or 0,st['cpu.cycleCount']-cycles1002,fetch1002,st.masterClock-tick1002,hash1002))
   work1002:flush()
  end
 end
""".replace("ORIGIN",str(ORIGIN)))
    return lua
