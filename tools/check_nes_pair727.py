"""Linked shared map epilogue versus726C, plus whole linked Flash/RAM ledger.

Directed masks exercise gaps, short second spans, 32/64-bit boundaries and
all four modes. Independent peer checks exact payload, CRC and four credits.
Full production/planner/IRQ/65816 timing is checked separately.
"""
import argparse,json
from pathlib import Path
from check_nes_supply723 import Row
from check_nes_rows713 import Peer
from analyze_nes_rows713 import resources
from nes_schedule492 import funcs
from nes_raw506 import sha

def direct(src,mask,mode):
 m=Row(src,'normal');e=m.endpoint=Peer('normal')
 for n,v in [('bank_history',2),('ending',1),('finished',1)]:m.put(m.p,'nes_plan200',n,v,1)
 m.put(m.s,'nes_native_sink165','plan',m.p,4)
 m.put(m.s,'nes_native_sink165','map_pair683',1,1)
 m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],bytes((2,2))+bytes(8))
 m.u.mem_write(m.video+m.layout['nes_native_video165']['map'],e.data)
 ok=m.call('map527',[m.s,m.video,mask&0xffffffff,mask>>32,mode]);assert ok
 assert not m.get(m.s,'nes_native_sink165','displayed') and not e.rearmed
 if mode:assert len(e.maps)<= (2 if mode==3 else 1)
 if mode==3 and len(e.maps)==2:assert e.maps[0][1]==e.maps[1][1]==192 and e.maps[1][0]==e.maps[0][0]+192
 return dict(maps=e.maps,calls=e.calls,cursor=m.get(m.s,'nes_native_sink165','map_next'),pair=m.get(m.s,'nes_native_sink165','map_pair683'),sequence=m.get(m.s,'nes_native_sink165','sequence',2))

def run(a):
 names=json.loads((a.reference/'pair-resources01.json').read_text())['C']['whole_functions']
 res={}
 for k,p in [('base_normal',a.base_normal),('base_long',a.base_long),('normal',a.normal),('long',a.arm)]:
  q=res[k]=resources(p);f=funcs(p/'obj-nes-100/sd2snes.elf')
  # Static functions can share names across translation units. Select the
  # documented largest status() (278B), not the unrelated36B name collision.
  q['whole_functions']={n:max([x[2] for x in f if x[0]==n],default=0) for n in names}
  assert q['whole_functions']['status']==278
  q['whole_boundary_B']=sum(q['whole_functions'].values())
 for old,new in [('base_normal','normal'),('base_long','long')]:
  b,c=res[old],res[new]
  assert c['Flash_B']<=212992 and c['whole_boundary_B']<=4700
  assert c['sections']==b['sections'] and c['structs']==b['structs']
  assert c['functions']['nes_sink527_early']==0
 masks=(0,0x3f,0x7f,0xf,0x77,7<<61,63<<58,63<<30)
 rows=[]
 for mask in masks:
  for mode in range(4):
   before=direct(a.reference/'normal04/src',mask,mode);after=direct(a.normal,mask,mode)
   assert before==after,(hex(mask),mode,before,after)
   rows.append(dict(mask=hex(mask),mode=mode,same=True,result=after))
 a.out.write_text(json.dumps(dict(stage=727,passed=True,scope=__doc__,resources=res,directed=rows,reference=sha(a.reference/'normal04/src/obj-nes-100/firmware.stm')),indent=2)+'\n')
 print('PASS727: whole normal/long Flash/RAM;32 linked map transition comparisons')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('reference','base-normal','base-long','normal','arm','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
