"""Defer ordinary BG/OBJ row/alt construction until an exact slot miss.

Keep original map/plan ordering and all source/tag/slot/epoch checks.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

def run(a):
 assert sha(a.base/'obj-nes-100/firmware.stm') in ('b5c42303c6831190f77c95367bd1640e3e575caea8e3909af27e2587ad5eb600','a1408f18a82602aa54fb67607c933c7dd5de79213e43adc1d2ee185ca3ae712a')
 names=('nes_planner211.c','nes_resident211.c','nes_resident211.h');f={n:(a.base/n).read_text() for n in names}
 n='nes_resident211.h';f[n]=once(f[n],'uint64_t,struct nes_plan191 *);','uint64_t,struct nes_plan191 *,bool rows_ready);')
 n='nes_resident211.c';s=once(f[n],'uint64_t exact,struct nes_plan191 *q){','uint64_t exact,struct nes_plan191 *q,bool rows_ready){')
 s=once(s,'q->kind>2)return UINT16_MAX;','q->kind>2||(!rows_ready&&q->kind==2))return UINT16_MAX;')
 s=once(s,' if(exact_slot!=stop)return exact_slot;',''' if(exact_slot!=stop)return exact_slot;
 /*716 Internal callers may defer the ordinary identity rows, not tag/key
  * validation or destination ownership. Exact hits need no descriptor at
  * all. Misses initialize every row/alt byte before classification/callback.
  * Exceptional BG and zero already carry fully defined shapes. */
 if(!rows_ready){
  for(unsigned i=0;i<8;i++){
   q->row[i*2]=q->row[i*2+1]=(uint8_t)i;q->alt[i]=UINT16_MAX;
  }
 }''');f[n]=s
 n='nes_planner211.c';s=f[n]
 s=once(s,'nes_resident211_slot(resident,p,0,&q)','nes_resident211_slot(resident,p,0,&q,true)')
 s=once(s,'''  for(unsigned f=0;f<8;f++)q.alt[f]=65535;
  uint8_t *mapping=q.row;for(unsigned f=0;f<8;f++){mapping[f*2]=(uint8_t)f;mapping[f*2+1]=(uint8_t)f;}
  uint64_t key=(cell&8191)|UINT64_C(0x1fed6c8da4480000);
  if((exceptional>>x)&1){''','''  uint64_t key=(cell&8191)|UINT64_C(0x1fed6c8da4480000);
  bool rows_ready=((exceptional>>x)&1)!=0;
  if(rows_ready){
  for(unsigned f=0;f<8;f++)q.alt[f]=65535;
  uint8_t *mapping=q.row;for(unsigned f=0;f<8;f++){mapping[f*2]=(uint8_t)f;mapping[f*2+1]=(uint8_t)f;}''')
 s=once(s,'nes_resident211_slot(resident,p,key,&q)','nes_resident211_slot(resident,p,key,&q,rows_ready)')
 s=once(s,'   for(unsigned f=0;f<8;f++){q.row[f*2]=q.row[f*2+1]=(uint8_t)f;q.alt[f]=65535;}\n','')
 s=once(s,'nes_resident211_slot(resident,p,tag|((unsigned)masks[e]<<13),&q)','nes_resident211_slot(resident,p,tag|((unsigned)masks[e]<<13),&q,false)')
 s=once(s,'} /* full exceptional row mapping; ordinary q.row remains identity */','} /* Exceptional shape is complete; ordinary rows are filled on a miss. */');f[n]=s
 if a.variant=='b':
  # One real constructor serves exceptional caller and write-required miss.
  # Retained-bank hits keep the header/ownership checks without constructing
  # and then rechecking the ordinary constant shape that will not be sent.
  n='nes_resident211.c';s=f[n]
  block=''' if(!rows_ready){
  for(unsigned i=0;i<8;i++){
   q->row[i*2]=q->row[i*2+1]=(uint8_t)i;q->alt[i]=UINT16_MAX;
  }
 }'''
  s=once(s,block,'')
  s=once(s,'static bool ordinary(const struct nes_plan191 *q){','''void __attribute__((noinline)) nes_resident716_rows(struct nes_plan191 *q){
 for(unsigned i=0;i<8;i++){
  q->row[i*2]=q->row[i*2+1]=(uint8_t)i;q->alt[i]=UINT16_MAX;
 }
}
static bool ordinary(const struct nes_plan191 *q,bool rows_ready){''')
  s=once(s,' for(unsigned i=0;i<8;i++)if(q->alt[i]!=UINT16_MAX)return false;',' if(!rows_ready)return true;\n for(unsigned i=0;i<8;i++)if(q->alt[i]!=UINT16_MAX)return false;')
  s=once(s,'bool retain=ordinary(q);','bool retain=ordinary(q,rows_ready);')
  s=once(s,' q->slot=(uint16_t)slot;',' if(!rows_ready)nes_resident716_rows(q);\n q->slot=(uint16_t)slot;')
  f[n]=s
  n='nes_planner211.c';s=f[n]
  s=once(s,'''  for(unsigned f=0;f<8;f++)q.alt[f]=65535;
  uint8_t *mapping=q.row;for(unsigned f=0;f<8;f++){mapping[f*2]=(uint8_t)f;mapping[f*2+1]=(uint8_t)f;}''','''  nes_resident716_rows(&q);
  uint8_t *mapping=q.row;''');f[n]=s
  n='nes_resident211.h';f[n]=once(f[n],'bool nes_resident211_prepare(', 'void nes_resident716_rows(struct nes_plan191 *);\nbool nes_resident211_prepare(')
 a.out.mkdir(parents=True,exist_ok=False)
 for n,s in f.items():(a.out/n).write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage=716,variant=a.variant,base={n:sha(a.base/n) for n in names},patch={n:sha(a.out/n) for n in names},new_static_RAM_B=0,new_SPI_opcode=False,extra_internal_argument_B=4),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--variant',choices=('a','b'),default='a')
 run(p.parse_args())
