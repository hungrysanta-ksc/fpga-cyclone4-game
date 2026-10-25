# SPDX-License-Identifier: MIT
"""Actual M4 prior-bank OBJ deficit probe. No future plan is producer input.

Storage/packet and schedule are diagnostic budgets, not a connected EA path.
"""
import argparse,binascii,inspect,json,shutil,struct
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_hint360 import decoder
from probe_nes_arm264 import ARM,ELFFile
import probe_nes_decode280 as old

OBJ=r'''
uint16_t obj_tags362[2];unsigned obj_count362,obj_cursor362,obj_done362;
void obj_reset362(void){obj_count362=obj_cursor362=obj_done362=0;}
unsigned obj_hint362(const struct nes_resident211 *r,unsigned epoch,unsigned prior_serial,unsigned immutable){
 State *s=&receiver280;
 if(!immutable||obj_done362||prior_serial<2||s->cold||(s->phase!=1&&s->phase!=2)||
    !r->displayed||r->open||r->prepared||r->fault||r->active>1||r->obj_slots>128||
    r->epoch!=epoch||s->epoch!=epoch||r->serial!=prior_serial||prior_serial==UINT32_MAX||prior_serial+1!=s->serial)return 0;
 unsigned target=1-r->active,steps=0;
 while(obj_cursor362<r->obj_slots&&steps++<16&&obj_count362<2){
  unsigned i=obj_cursor362++,index=1024+i,key=r->obj[i];
  if(key==UINT32_MAX||!(r->resident[r->active][index/8]&(1u<<(index%8)))||
     (r->resident[target][index/8]&(1u<<(index%8))))continue;
  unsigned tag=key&8191,j;
  for(j=0;j<obj_count362;j++)if(obj_tags362[j]==tag)break;
  if(j==obj_count362)obj_tags362[obj_count362++]=(uint16_t)tag;
 }
 obj_done362=obj_cursor362==r->obj_slots||obj_count362==2;return obj_count362;
}
unsigned obj_packet362(void){
 if(obj_count362!=2||packet360[1]!=5)return 0;
 packet360[1]=7;
 for(unsigned i=0;i<2;i++){packet360[22+i*2]=(uint8_t)obj_tags362[i];packet360[23+i*2]=(uint8_t)(obj_tags362[i]>>8);}
 uint16_t c=65535;for(unsigned i=0;i<26;i++)c=crc(c,packet360[i]);packet360[26]=(uint8_t)c;packet360[27]=(uint8_t)(c>>8);return 28;
}
'''

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 for p in (BASE/'probes/nes-raster355/fixed01').glob('*.h'):shutil.copyfile(p,d/p.name)
 s=inspect.getsource(old.build).replace("shutil.copyfile(ROOT/'tools/nes_decode280.c',d/'nes_decode280.c')","(d/'nes_decode280.c').write_text(decoder(),newline='\\n')")
 ns=dict(old.__dict__);ns['decoder']=lambda:decoder(5).replace('packet360[24]','packet360[28]')+OBJ;exec(compile(s,'obj362-build','exec'),ns);ns['build'](d)
 rows=[];pins={};guards=[]
 for mode in ('window04','fixed01'):
  src=BASE/'probes/nes-hint361'/mode;blob=(src/'hint-consumed-prior361.bin').read_bytes();ref=ARM(src/'output.elf',None);arm=ARM(d/'decoder.elf',None)
  with (src/'output.elf').open('rb') as fp:
   syms=ELFFile(fp).get_section_by_name('.symtab');sizes={n:syms.get_symbol_by_name(n)[0]['st_size'] for n in ('receiver280','resident285')}
  for n,address,length in [('receiver280',arm.symbols['receiver280'],sizes['receiver280']),('history286',0x20010000,4910),('resident285',0x20020000,sizes['resident285'])]:
   off=ref.symbols[n]-0x20000000;arm.uc.mem_write(address,blob[off:off+length])
  prior=bytes(arm.uc.mem_read(0x20020000,sizes['resident285']))
  block=bytes(int(x,16) for x in (src/'hint-block361.hex').read_text().split());arm.uc.mem_write(0x20018000,block)
  before=arm.instructions;assert arm.call('block280',[0x20010000,0x20018000,len(block),binascii.crc_hqx(block,65535)])==1;decode_cost=arm.instructions-before
  snapshot=(bytes(arm.uc.mem_read(0x20000000,0x40000)),arm.uc.context_save())
  before=arm.instructions;arm.call('obj_reset362',[]);calls=[]
  for i in range(8):
   at=arm.instructions;n=arm.call('obj_hint362',[0x20020000,1,2,1]);calls.append(arm.instructions-at)
   if int.from_bytes(arm.uc.mem_read(arm.symbols['obj_done362'],4),'little'):break
  total=arm.instructions-before;tags=list(struct.unpack('<'+'H'*n,bytes(arm.uc.mem_read(arm.symbols['obj_tags362'],2*n))))
  assert bytes(arm.uc.mem_read(0x20020000,sizes['resident285']))==prior
  rows.append(dict(mode=mode,tags=tags,calls=calls,extra_instructions=total,source_decode_instructions=decode_cost,observed_stack=0x2003f000-arm.low_sp))
  for label,args in [('epoch',[0x20020000,2,2,1]),('serial',[0x20020000,1,1,1]),('mutable',[0x20020000,1,2,0]),('STOP',[0x20020000,1,2,1])]:
   arm.uc.mem_write(0x20000000,snapshot[0]);arm.uc.context_restore(snapshot[1]);arm.call('obj_reset362',[])
   if label=='STOP':arm.call('reset280',[])
   assert arm.call('obj_hint362',args)==0;guards.append(mode+':'+label)
  for p in (src/'hint-consumed-prior361.bin',src/'output.elf',src/'hint-block361.hex'):pins[str(p)]=sha(p)
 for p in (d/'decoder.elf',d/'nes_decode280.c',ROOT/'tools/probe_nes_obj362.py'):pins[str(p)]=sha(p)
 r=dict(passed=True,rows=rows,guards=guards,size=(d/'size.log').read_text(),pins=pins,live_SPI=False,scope=__doc__)
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps({k:v for k,v in r.items() if k!='pins'},indent=2))
if __name__=='__main__':main()
