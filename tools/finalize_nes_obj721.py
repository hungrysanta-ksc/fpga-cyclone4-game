"""Compact721 decision; preserve full packet/CPU traces in local archive."""
import argparse,json
from pathlib import Path
from nes_raw506 import sha
from analyze_nes_rows713 import resources
from nes_schedule492 import funcs

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();r=json.loads((a.probe/'schedule02.json').read_text())
 r['guards']={}
 for name,path in [('admission',a.probe/'deadline01.json'),('normal_menu',a.probe/'normal-menu01.json'),('bulk_policy',a.probe/'tail01.json'),
  ('inherited_slots',a.probe.parent/'nes-supply720/lazy01.json'),('plan',a.probe/'ownership01.json'),('credit',a.probe/'credit01.json'),
  ('runtime',a.probe/'runtime01.json'),('menu',a.probe/'menu01.json'),('MAP_query',a.probe/'query01.json'),
  ('STOP',a.temp/'nes-obj721-stop01/result.json'),('inherited_same_65816_exit',a.temp/'nes-idle718-exit01/result.json')]:
  r['guards'][name]=dict(SHA256=sha(path),result=json.loads(path.read_text()))
 for phase in r['phases'].values():
  for label in ('original','previous','candidate'):
   phase[label]['details']={g:{k:v for k,v in d.items() if k in ('previous_reveal','interval','early_DMA','relative_ms','BG_ROM_reads','map_packet_B','marks','next_budget721')} for g,d in phase[label]['details'].items()}
  phase['input_borrow']={g:dict(calls=len(xs),duration_ms=sum(x['duration_ms'] for x in xs),checked_blocks=sum(x['checked_blocks'] for x in xs),DMA_notices=sum(len(x['DMA_notices']) for x in xs)) for g,xs in phase['input_borrow'].items()}
 r['resource_only_candidates']={v:dict(resources=resources(a.probe/name/'src'),two_phase_timing_run=False,reason='Normal Flash exceeds212992B; no full timing/installer qualification') for v,name in [('B','normal-b01'),('C','normal-c01'),('D','normal-d01'),('E','normal-e01')]}
 r['resource_only_candidates']['D']['guards']=json.loads((a.probe/'gate-d01.json').read_text())
 assert all(x['resources']['Flash_B']>212992 for x in r['resource_only_candidates'].values())
 def boundary(src):
  extras={k[0]:k[2] for k in funcs(src/'obj-nes-100/sd2snes.elf') if k[0] in ('poll','send')}
  assert len(extras)==2
  named=resources(src)['boundary_B']
  return dict(named_subset_B=named,extra_functions_B=extras,whole_B=named+sum(extras.values()))
 r['same_boundary_ledger']={v:boundary(a.probe/name/'src') for v,name in [('A','normal01'),('B','normal-b01'),('C','normal-c01'),('D','normal-d01'),('E','normal-e01')]}
 old=boundary(a.probe.parent/'nes-deadline719/normal04/src');r['same_boundary_ledger']['719']=old
 cap=old['whole_B']+(1116-old['named_subset_B']);r['same_boundary_cap_B']=cap
 for v,x in r['resource_only_candidates'].items():
  x.update(resource_gate=False,Flash_deficit_B=x['resources']['Flash_B']-212992,boundary_deficit_B=max(0,r['same_boundary_ledger'][v]['whole_B']-cap))
 r['boundary_note']='Include poll/send changed by D/C on both sides; named old subset alone is not the replacement cost. Prior archive01 omitted this helper deletion from the boundary decision.'
 r['board']='707D and existing65816 unchanged; whole FIT/STA inherited from analysis/bg707-verification.json. No new physical or external IO claim.'
 r['complete_CPU_frames']=106
 r['tools']={p.name:sha(p) for p in Path('tools').glob('*721*.py')}
 a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
 print('721 finalized; selected',r['selected'])
