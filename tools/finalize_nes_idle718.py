"""Compact718 decision evidence; full packet and CPU records remain archived."""
import argparse,json
from pathlib import Path
from nes_raw506 import sha

def run(a):
 variants={name:json.loads((a.probe/file).read_text()) for name,file in [('A','schedule01.json'),('B','schedule-b01.json')]}
 r=dict(stage=718,variants=variants,selected=any(v['selected'] for v in variants.values()),physical_FPS=False,new_installer=False)
 r['guards']={}
 for n,p in [('input_DMA_boundary',a.probe/'guards04.json'),('bulk_policy',a.probe/'policy01.json'),
  ('slots',a.probe/'slots01.json'),('plan',a.probe/'plan01.json'),('runtime',a.probe/'runtime01.json'),
  ('menu',a.probe/'menu01.json'),('recipe',a.probe/'repro02.json'),
  ('B_boundary',a.probe/'guards-b01.json'),('B_credit',a.probe/'credit-b01.json'),('B_bulk',a.probe/'policy-b01.json'),
  ('B_runtime',a.probe/'runtime-b01.json'),('B_menu',a.probe/'menu-b01.json'),('B_slots',a.probe/'slots-b01.json'),
  ('B_plan',a.probe/'plan-b01.json'),
  ('B_recipe',a.probe/'repro-b01.json'),('B_STOP',a.temp/'nes-idle718-stop-b01/result.json'),
  ('STOP',a.temp/'nes-idle718-stop01/result.json'),('exit',a.temp/'nes-idle718-exit01/result.json')]:
  r['guards'][n]=dict(SHA256=sha(p),result=json.loads(p.read_text()))
 for variant in variants.values():
  for phase in variant['phases'].values():
   for label in ('original','previous','candidate'):
    for detail in phase[label]['details'].values():
     detail.pop('packets',None);detail.pop('DMA_events',None)
 r['board']='707D and existing65816 unchanged; full FIT/STA inherited from analysis/bg707-verification.json. No new external IO or physical FPS claim.'
 r['tools']={p.name:sha(p) for p in Path('tools').glob('*718*.py')}
 a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
 print('718 evidence finalized; selected',r['selected'])

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
