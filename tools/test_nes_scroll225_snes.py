# SPDX-License-Identifier: MIT
"""Actual225 C planner/sink -> unchanged212 65816; visible pixels vs186.
Reuse the established packet/ACK/VRAM/VBlank harness, add circular scroll.
"""
import inspect
from pathlib import Path
import test_nes_dirty212 as prior
from nes_scroll225 import ROOT,BASE,sha,planner,once

SCROLL=[0,1,7,8,15,31,32,33,62,63,0,63,32,31,4,0]

def body225(body):
    body=once(body,' source(variant,gen);convert_input();',''' source(variant<8?variant:2,gen);
 if(variant>=8){
  static const unsigned positions[]={0,1,7,8,15,31,32,33,62,63,0,63,32,31,4,0};
  unsigned coarse=positions[gen-15];r.ntiles=128;r.counts[0]=28*33;r.counts[3]=0;
  for(unsigned t=0;t<128;t++){r.tiles[t].tag=(uint16_t)t;r.tiles[t].kind=3;
   for(unsigned j=0;j<16;j++)r.tiles[t].data[j]=(uint8_t)(t*31+j*13);}
  for(unsigned y=0;y<224;y++){
   r.rows[y]=(uint8_t)(((y/8)<<3)|(y&7));
   r.raster[y]=(UINT64_C(0x1e)<<36)|((uint64_t)(gen&7)<<30)|(coarse&31)|((coarse&32)<<5);
  }
  for(unsigned y=0;y<28;y++)for(unsigned x=0;x<33;x++)
   r.maps[y*33+x]=(uint16_t)(((y*3+x+coarse)%128)|(((x+coarse)%4)<<13));
 }
 convert_input();''')
    body=once(body,'const unsigned variants[]={0,0,0,2,2,2,3,4,5,6,7,0,0,0};',
        'const unsigned variants[]={0,0,0,2,2,2,3,4,5,6,7,0,0,0,'+','.join(['8']*16)+'};')
    return body

def prepare225(common):
    prior.prepare(common)
    src=BASE/'probes/nes-ingress223/arm01/src'
    for n in ['nes_resident211.c','nes_resident211.h','nes_native165.c','nes_native165.h','nes_planner211.c']:
        (common/n).write_bytes((src/n).read_bytes())
    p=common/'nes_planner211.c';p.write_text(planner(p.read_text()),encoding='utf8',newline='\n')

s=inspect.getsource(prior.main)
s=once(s,"common=out/'common';prepare(common)","common=out/'common';prepare225(common)")
s=once(s,"body=(ROOT/'tests/nes-functional/dirty212_host.c').read_text()", "body=body225((ROOT/'tests/nes-functional/dirty212_host.c').read_text())")
s=once(s,"tracked=[Path(__file__),ROOT/'tools/nes_dirty212.py',ROOT/'tools/nes_sink212.py',ROOT/'tests/nes-functional/dirty212_host.c']", "tracked=[Path(__file__),ROOT/'tools/nes_scroll225.py',ROOT/'tools/test_nes_dirty212.py',ROOT/'tools/nes_dirty212.py',ROOT/'tools/nes_sink212.py',ROOT/'tests/nes-functional/dirty212_host.c']")
# Thirty reference/candidate frames exceed the old14-frame runner wall budget.
s=s.replace('--timeout=55','--timeout=180').replace('m.wait(timeout=60)','m.wait(timeout=200)')
ns=dict(prior.__dict__);ns.update(__file__=__file__,__doc__=__doc__,prepare225=prepare225,body225=body225)
exec(compile(s,'scroll225-snes','exec'),ns)
if __name__=='__main__':ns['main']()
