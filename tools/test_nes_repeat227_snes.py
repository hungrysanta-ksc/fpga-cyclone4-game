# SPDX-License-Identifier: MIT
"""227 C packets to actual65816, scrolling pixels and malformed OAM rejection."""
import test_nes_scroll225_snes as prior
import nes_repeat227
from nes_repeat227 import ROOT,BASE,once

def prepare227(common):
    prior.prepare225(common)
    src=BASE/'probes/nes-fast226/arm01/src'
    for n in ['nes_planner211.c','nes_resident211.c','nes_resident211.h','nes_native165.c','nes_native165.h']:
        (common/n).write_bytes((src/n).read_bytes())

def sink227(d):
    src=BASE/'probes/nes-fast226/arm01/src/nes_native_sink165.c'
    (d/'nes_native_sink165.c').write_text(nes_repeat227.sink(src.read_text()),encoding='utf8',newline='\n')

def body227(body):
    body=prior.body225(body)
    return once(body,' return nes_sink212_seal(&sink,&candidate,&cache);', '''
 char name227[40];sprintf(name227,"oam-%u.bin",gen);
 FILE *f227=fopen(name227,"wb");assert(f227&&fwrite(candidate.oam,1,544,f227)==544);fclose(f227);
 return nes_sink212_seal(&sink,&candidate,&cache);''')

s=prior.s
s=s.replace("prepare225(common)","prepare227(common)")
s=s.replace("body=body225(", "body=body227(")
s=once(s,"  nes_sink212.prepare(d)","  nes_sink212.prepare(d)\n  if typ=='candidate':sink227(d)")
s=once(s," nes_dirty212.build(out/'client')"," nes_repeat227.build(out/'client')")
s=s.replace("['commits']==14","['commits']==30")
s=once(s," if CANDIDATE and pw(8)==2 then", """ if CANDIDATE and pw(8)==2 and pb(0)==8 then
  local b={packet:byte(1,#packet)}
  if MODE=='repeat_short' then b[15]=4;b[16]=0 end
  if MODE=='repeat_odd' then b[15]=b[15]|1 end
  if MODE=='repeat_section' then b[2]=3 end
  if MODE=='repeat_period' then b[13]=2 end
  if MODE=='repeat_overflow' then b[11]=0xfc;b[12]=1 end
  packet=string.char(table.unpack(b))
 end
 if CANDIDATE and pw(8)==2 then""")
s=once(s,"tracked=[Path(__file__),", "tracked=[ROOT/'tools/nes_repeat227.py',Path(__file__),")
s=once(s," lua=lua.replace('pw(8)==13','pw(8)==2')", """ lua=once(lua,"  if bytes:byte(1)==1 then",\"\"\"  if bytes:byte(1)==1 then
   if CANDIDATE then
    local f=assert(io.open(OUT_DIR..'/oam-'..pw(8)..'.bin','rb'));local want=f:read('*a');f:close();assert(#want==544)
    local base=0x10000+word(0x1020)+0x6200
    for i=0,543 do assert(rd(base+i)==want:byte(i+1),'exact candidate OAM mismatch '..i)end
   end
\"\"\")
 lua=lua.replace('pw(8)==13','pw(8)==2')""")
s=once(s," lua=lua.replace('pw(8)==13','pw(8)==2')", """ lua=lua.replace('pw(8)==13','pw(8)==2')
 lua=once(lua,' if a==0x6001 then',\" if a==0x6001 then\\n  if MODE=='stop_repeat' and packet and pb(0)==8 and pw(8)==2 then return 128 end\")""")
ns=dict(prior.ns);ns.update(__file__=__file__,__doc__=__doc__,prepare227=prepare227,
    sink227=sink227,body227=body227,nes_repeat227=nes_repeat227)
exec(compile(s,'repeat227-snes','exec'),ns)
if __name__=='__main__':ns['main']()
