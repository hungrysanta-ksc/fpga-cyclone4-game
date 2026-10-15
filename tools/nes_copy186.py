# SPDX-License-Identifier: MIT
"""Bounded fixed256 COPY6 groups; unchanged converter and FPGA queue.

Four exact64-byte dirty bits qualify a group. Any dirty bit sends that group
through the existing literal/RLE span. No variable-length copy or extra RAM.
"""
from pathlib import Path
import argparse,inspect,json,shutil
import nes_map185 as prior
from nes_clip178 import replace
from nes_game147 import sha

def source181(s):
 s=prior.source181(s)
 for a,b in [('checkimm(0x120e,64)','checkimm(0x120e,256)'),
             ('c.emit(0x29,63,0)','c.emit(0x29,255,0)'),
             ("imm(64);sta(0x120c);c.jump('data')","imm(256);sta(0x120c);c.jump('data')"),
             ('imm(63);c.emit(0x8b,0x54','imm(255);c.emit(0x8b,0x54'),
             ('c.emit(0xc9,0x51,0x18)','c.emit(0xc9,0x61,0x18)')]:s=replace(s,a,b)
 return s

def build(out):
 ns=dict(prior.pad.__dict__);ns['source181']=source181
 exec(compile(inspect.getsource(prior.pad.build),'copy186-build','exec'),ns)
 r=ns['build'](out);r.update(candidate='copy186',scope=__doc__,sink_version='1861',seal_version='1861',copy_bytes=256,metadata_end=0x1246,extra_persistent_ram=2)
 (out/'build.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');return r

MAP=r'''
static bool map185(struct nes_native_sink165 *s,const struct nes_native_video165 *p){
 if(!p->map_inherit)return span(s,2,0,p->map,4096);
 if(!s->displayed||p->map_base_generation!=s->last_generation)return fail(s,5);
 unsigned dirty=0;
 for(unsigned g=0;g<16;g++)if((p->map_dirty>>(g*4))&15)dirty|=1u<<g;
 unsigned cost=0;
 for(unsigned g=0;g<16;){
  if(!(dirty&(1u<<g))){cost+=487;g++;}
  else{unsigned first=g++;while(g<16&&(dirty&(1u<<g)))g++;
   cost+=span_cost185(p->map+first*256,(g-first)*256);}
 }
 if(cost>=span_cost185(p->map,4096))return span(s,2,0,p->map,4096);
 uint8_t base[2];put16(base,p->map_base_generation);
 for(unsigned g=0;g<16;){
  if(!(dirty&(1u<<g))){
   if(!packet_wire(s,6,2,g*256,base,2,256))return false;
   g++;
  }else{unsigned first=g++;while(g<16&&(dirty&(1u<<g)))g++;
   if(!span(s,2,first*256,p->map+first*256,(g-first)*256))return false;}
 }
 return true;
}
'''

def prepare(old,out):
 out.mkdir(parents=True,exist_ok=False);pins={}
 for f in sorted(old.glob('nes_*')):
  if f.is_file() and f.suffix in ('.c','.h'):shutil.copyfile(f,out/f.name);pins[f.name]=sha(f)
 f=out/'nes_native_sink165.c';s=f.read_text()
 start=s.index('static bool map185(');end=s.index('bool nes_sink165_seal(',start)
 s=s[:start]+MAP+'\n'+s[end:]
 s=replace(s,'at%64||expanded!=64','at%256||expanded!=256')
 s=replace(s,'put16(descriptor+20,0x1851)','put16(descriptor+20,0x1861)')
 f.write_text(s,encoding='utf8',newline='\n')
 r=build(out/'client');(out/'preparation.json').write_text(json.dumps(dict(input_pins=pins,client=r),indent=2)+'\n',encoding='utf8');return r
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();print(json.dumps(prepare(a.prior,a.out),indent=2))
