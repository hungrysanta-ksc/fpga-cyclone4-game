# SPDX-License-Identifier: MIT
"""Exact in-place map comparison and checked previous-display inheritance.

COPY6 copies one aligned64-byte map block from the last displayed WRAM image.
Its payload names the base generation. Strict monotonic session serial and
the terminal-on-error receiver make that base the preceding successful SEAL.
No second MCU frame, hash decision, VRAM skip or new FPGA allocation.
"""
from pathlib import Path
import argparse,inspect,json,shutil
import nes_pad185 as pad
from nes_clip178 import replace
from nes_game147 import sha


def source181(s):
 s=pad.source181(s)
 s=replace(s,"c.emit(0xc9,5,0);c.branch(0xf0,'packed_header181');",
             "c.emit(0xc9,5,0);c.branch(0xf0,'packed_header181');c.emit(0xc9,6,0);c.branch(0xf0,'packed_header181');")
 s=replace(s," c.emit(0xc9,5,0);cond(0xd0,'short_repeat1815');", """ c.emit(0xc9,6,0);cond(0xf0,'inherit185')
 c.emit(0xc9,5,0);cond(0xd0,'short_repeat1815');""")
 s=replace(s," c.label('begin');", """ c.label('inherit185');checkimm(0x1200,0x0206);checkimm(0x120c,2);checkimm(0x120e,64)
 lda(0x1024);c.emit(0x29,255,0);cond(0xf0,'bad_packet')
 c.long(0xaf,0x400010);cmp(0x1244);cond(0xd0,'bad_packet')
 lda(0x120a);c.emit(0x29,63,0);cond(0xd0,'bad_packet')
 imm(64);sta(0x120c);c.jump('data')
 c.label('begin');""")
 s=replace(s," c.emit(0xe2,0x20);c.store(0x2183,1)", """ # A still holds the validated destination WRAM offset from STA2181.
 c.emit(0xa8);lda(0x1200);c.emit(0xc9,6,2);c.branch(0xd0,'ordinary185')
 # BEGIN selects the opposite 32KiB WRAM bank. Inheritance requires a
 # displayed base, so toggling its validated destination recovers source.
 c.emit(0x98,0x49,0,0x80,0xaa)
 imm(63);c.emit(0x8b,0x54,0x7f,0x7f,0xab);c.jump('accepted')
 c.label('ordinary185');c.emit(0xe2,0x20);c.store(0x2183,1)""")
 s=replace(s," lda(0x1240);sta(0x1242)"," lda(0x1226);sta(0x1244)\n lda(0x1240);sta(0x1242)")
 return replace(s,'c.emit(0xc9,0x15,0x18)','c.emit(0xc9,0x51,0x18)')


def build(out):
 ns=dict(pad.__dict__);ns['source181']=source181
 exec(compile(inspect.getsource(pad.build),'map185-build','exec'),ns)
 r=ns['build'](out)
 r.update(scope=__doc__,candidate='map185',sink_version='1851',seal_version='1851',metadata_end=0x1246,extra_persistent_ram=2)
 (out/'build.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');return r


MAP=r'''
static unsigned span_cost185(const uint8_t *b,unsigned n){
 unsigned old=0,planned=0;
 for(unsigned at=0;at<n;){unsigned k=n-at;if(k>240)k=240;old+=data_cost(b+at,k);at+=k;}
 for(unsigned at=0;at<n;){unsigned k=span_piece(b+at,n-at);planned+=data_cost(b+at,k);at+=k;}
 return old<planned?old:planned;
}
static bool map185(struct nes_native_sink165 *s,const struct nes_native_video165 *p){
 if(!p->map_inherit)return span(s,2,0,p->map,4096);
 if(!s->displayed||p->map_base_generation!=s->last_generation)return fail(s,5);
 unsigned cost=0;
 for(unsigned block=0;block<64;){
  if(!(p->map_dirty&(UINT64_C(1)<<block))){cost+=487;block++;}
  else{unsigned first=block++;while(block<64&&(p->map_dirty&(UINT64_C(1)<<block)))block++;
   cost+=span_cost185(p->map+first*64,(block-first)*64);}
 }
 /* Same conservative cost units as span(); never inflate a highly repeated
  * map merely to use inheritance. Dirty blocks remain fully literal/RLE. */
 if(cost>=span_cost185(p->map,4096))return span(s,2,0,p->map,4096);
 uint8_t base[2];put16(base,p->map_base_generation);
 for(unsigned block=0;block<64;){
  if(!(p->map_dirty&(UINT64_C(1)<<block))){
   if(!packet_wire(s,6,2,block*64,base,2,64))return false;
   block++;
  }else{unsigned first=block++;while(block<64&&(p->map_dirty&(UINT64_C(1)<<block)))block++;
   if(!span(s,2,first*64,p->map+first*64,(block-first)*64))return false;}
 }
 return true;
}
'''


def prepare(prior,out):
 out.mkdir(parents=True,exist_ok=False);pins={}
 for p in prior.glob('nes_*.h'):shutil.copyfile(p,out/p.name);pins[p.name]=sha(p)
 for n in ['nes_native165.c','nes_trace166.c','nes_sink_trace168.c','nes_sink_window184.c','nes_native_runtime165.c']:
  shutil.copyfile(prior/n,out/n);pins[n]=sha(prior/n)
 def edit(n,fn):
  s=(prior/n).read_text();pins[n]=sha(prior/n);(out/n).write_text(fn(s),encoding='utf8',newline='\n')
 def header(s):
  s=replace(s,' uint16_t hofs[224],vofs[224];',' uint64_t map_dirty;uint16_t map_base_generation;bool map_inherit;\n uint16_t hofs[224],vofs[224];')
  return replace(s,'#endif','bool nes_native_video185_build(const struct nes_native165 *,const uint16_t palette64[64],struct nes_native_video165 *,bool,nes_native_video165_stage_fn,void *);\n#endif')
 edit('nes_native_video165.h',header)
 def video(s):
  s=replace(s,'bool nes_native_video165_build(', 'bool nes_native_video185_build(')
  s=replace(s,'struct nes_native_video165 *p,nes_native_video165_stage_fn stage','struct nes_native_video165 *p,bool inherit,nes_native_video165_stage_fn stage')
  s=replace(s,' memset(p,0,sizeof(*p));p->generation=s->generation;', ''' if(inherit&&!p->valid)return fail(p,17);
 uint16_t base=inherit?p->generation:0;
 /* Keep only the old map; every other byte retains the original zero-init.
  * Caller may request inheritance only after the preceding display ACK. */
 memset(p,0,offsetof(struct nes_native_video165,map));
 memset((uint8_t *)p+offsetof(struct nes_native_video165,oam),0,sizeof(*p)-offsetof(struct nes_native_video165,oam));
 if(!inherit)memset(p->map,0,sizeof(p->map));
 p->map_dirty=inherit?0:UINT64_MAX;p->map_inherit=inherit;p->map_base_generation=base;p->generation=s->generation;''')
  s=replace(s,'#include <string.h>','#include <string.h>\n#include <stddef.h>\nstatic void map_word185(struct nes_native_video165 *p,unsigned at,unsigned word){\n if(p->map[at]!=(uint8_t)word||p->map[at+1]!=(uint8_t)(word>>8))p->map_dirty|=UINT64_C(1)<<(at/64);\n p->map[at]=(uint8_t)word;p->map[at+1]=(uint8_t)(word>>8);\n}')
  s=replace(s,' p->groups=(uint8_t)groups;p->bg_count=1;',''' p->groups=(uint8_t)groups;p->bg_count=1;
 /* Explicitly clear cells omitted by this generation, including shrink. */
 for(unsigned g=0;g<32;g++)for(unsigned x=0;x<64;x++)
  if(g>=groups||x>=33)map_word185(p,((x/32)*1024+g*32+x%32)*2,0);''')
  s=replace(s,'put16(p->map+at,slot|','map_word185(p,at,slot|')
  return s+'''\nbool nes_native_video165_build(const struct nes_native165 *s,const uint16_t lut[64],struct nes_native_video165 *p,nes_native_video165_stage_fn stage,void *ctx){
 return nes_native_video185_build(s,lut,p,false,stage,ctx);
}\n'''
 edit('nes_native_video165.c',video)
 edit('nes_native_sink165.h',lambda s:replace(s,'uint16_t generation,sequence,bg_next,obj_next;','uint16_t generation,sequence,bg_next,obj_next,last_generation;'))
 def sink(s):
  s=replace(s,' if(op!=5 && expanded)return fail(s,1);',' if(op==6&&(!data||n!=2||section!=2||at%64||expanded!=64))return fail(s,1);\n if(op!=5&&op!=6&&expanded)return fail(s,1);')
  s=replace(s,'b[0]==2||b[0]==4||b[0]==5','b[0]==2||b[0]==4||b[0]==5||b[0]==6')
  s=replace(s,'bool nes_sink165_seal(',MAP+'\nbool nes_sink165_seal(')
  s=replace(s,' for(unsigned k=2;k<6;k++)if(!span(s,k,0,data[k-2],size[k]))return false;',
              ' if(!map185(s,p))return false;\n for(unsigned k=3;k<6;k++)if(!span(s,k,0,data[k-2],size[k]))return false;')
  s=replace(s,'put16(descriptor+20,0x1815)','put16(descriptor+20,0x1851)')
  return replace(s,' s->displayed=true;s->state=NES_SINK165_IDLE;',' s->last_generation=s->generation;s->displayed=true;s->state=NES_SINK165_IDLE;')
 edit('nes_native_sink165.c',sink)
 edit('nes_sink_window184.c',lambda s:replace(s,'p[0]!=2&&p[0]!=4&&p[0]!=5','p[0]!=2&&p[0]!=4&&p[0]!=5&&p[0]!=6'))
 edit('nes_native_runtime165.c',lambda s:replace(s,'nes_native_video165_build(r,s->palette,s->video,','nes_native_video185_build(r,s->palette,s->video,s->sink.displayed,'))
 r=build(out/'client');(out/'preparation.json').write_text(json.dumps(dict(input_pins=pins,client=r),indent=2)+'\n',encoding='utf8')
 return r

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();print(json.dumps(prepare(a.prior,a.out),indent=2))
