"""Compact720 decision; preserve full packet/CPU traces in local archive."""
import argparse,json
from pathlib import Path
from nes_raw506 import sha

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();r=json.loads((a.probe/'schedule04.json').read_text())
 r['guards']={}
 for name,path in [('admission',a.probe/'deadline01.json'),('normal_menu',a.probe/'normal-menu01.json'),('bulk_policy',a.probe/'tail01.json'),
  ('slots',a.probe/'lazy01.json'),('plan',a.probe/'ownership01.json'),('credit',a.probe/'credit01.json'),
  ('runtime',a.probe/'longrun01.json'),('menu',a.probe/'menu01.json'),('MAP_query',a.probe/'query03.json'),
  ('STOP',a.temp/'nes-supply720-stop01/result.json'),('inherited_same_65816_exit',a.temp/'nes-idle718-exit01/result.json')]:
  r['guards'][name]=dict(SHA256=sha(path),result=json.loads(path.read_text()))
 for phase in r['phases'].values():
  for label in ('original','previous','candidate'):
   phase[label]['details']={g:{k:v for k,v in d.items() if k in ('previous_reveal','interval','early_DMA','relative_ms','BG_ROM_reads','map_packet_B','marks','next_budget720')} for g,d in phase[label]['details'].items()}
  phase['input_borrow']={g:dict(calls=len(xs),duration_ms=sum(x['duration_ms'] for x in xs),checked_blocks=sum(x['checked_blocks'] for x in xs),DMA_notices=sum(len(x['DMA_notices']) for x in xs)) for g,xs in phase['input_borrow'].items()}
 r['board']='707D and existing65816 unchanged; whole FIT/STA inherited from analysis/bg707-verification.json. No new physical or external IO claim.'
 r['complete_CPU_frames']=106
 r['tools']={p.name:sha(p) for p in Path('tools').glob('*720*.py')}
 a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
 print('720 finalized; selected',r['selected'])
