"""716B plus remove only fill-triggered full queue drain before ready tile.

Retain map drain, bulk receipt, queue admission, STOP and final ACK checks.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

def run(a):
 assert sha(a.base/'obj-nes-100/firmware.stm') in (
  'e31bccd000e682ad5ec6da95ebc0bd801bfd760f0fe51dfb06db37581524dca9',
  '65fa49cb9c985e6d383fcb7a870f66b6f0fa66a7b973ba33bfc5ad4bd70ec01a')
 name='nes_plan_service200.c';s=(a.base/name).read_text()
 s=once(s,'(p->window->last[1]==2 || (p->window->last[1]==5 && p->window->last[0]==5))','p->window->last[1]==2')
 s=once(s,'descriptor on this stack, retire the real map or immutable fill queue, and service one',
          'descriptor on this stack, retire the real map queue, and service one')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/name).write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage=717,base=sha(a.base/name),patch=sha(a.out/name),
  changed=[name],new_static_RAM_B=0,new_RTL=False,new_65816=False,policy='ready tile no longer drains preceding ordinary fill; map drain and bulk receipt retained'),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
