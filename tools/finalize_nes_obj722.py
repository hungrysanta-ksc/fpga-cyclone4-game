"""722 same-boundary cost and decision, full traces retained in private archive."""
import argparse,json
from pathlib import Path
from nes_raw506 import sha
from analyze_nes_rows713 import resources
from nes_schedule492 import funcs

def boundary(src):
 extras={k[0]:k[2] for k in funcs(src/'obj-nes-100/sd2snes.elf') if k[0] in ('poll','send','flush')}
 assert len(extras)==3
 named=resources(src)['boundary_B']
 return dict(named_subset_B=named,extra_functions_B=extras,whole_B=named+sum(extras.values()))

def run(a):
 r=json.loads((a.probe/'schedule01.json').read_text());r['guards']={}
 for name,path in [('CRC',a.probe/'crc01.json'),('DMA_gate',a.probe/'gate01.json'),('normal_DMA_gate',a.probe/'normal-gate01.json'),
  ('admission',a.probe/'deadline01.json'),('normal_menu',a.probe/'normal-menu01.json'),('bulk_policy',a.probe/'tail01.json'),
  ('inherited_slots',a.probe.parent/'nes-supply720/lazy01.json'),('plan',a.probe/'ownership01.json'),('credit',a.probe/'credit01.json'),
  ('runtime',a.probe/'runtime01.json'),('menu',a.probe/'menu01.json'),('STOP',a.temp/'nes-obj722-stop01/result.json'),
  ('inherited_same_65816_exit',a.temp/'nes-idle718-exit01/result.json')]:
  r['guards'][name]=dict(SHA256=sha(path),result=json.loads(path.read_text()))
 for phase in r['phases'].values():
  for label in ('original','previous','candidate'):
   phase[label]['details']={g:{k:v for k,v in d.items() if k in ('previous_reveal','interval','early_DMA','relative_ms','BG_ROM_reads','map_packet_B','marks','next_budget721')} for g,d in phase[label]['details'].items()}
  phase['input_borrow']={g:dict(calls=len(xs),duration_ms=sum(x['duration_ms'] for x in xs),checked_blocks=sum(x['checked_blocks'] for x in xs),DMA_notices=sum(len(x['DMA_notices']) for x in xs)) for g,xs in phase['input_borrow'].items()}
 paths={'719':a.probe.parent/'nes-deadline719/normal04/src','721D':a.probe.parent/'nes-obj721/normal-d01/src',
  '722A':a.probe/'normal01/src','722B':a.probe/'normal02/src','722C':a.probe/'normal03/src'}
 r['same_boundary_ledger']={n:boundary(p) for n,p in paths.items()}
 r['same_boundary_cap_B']=1744+172
 r['expanded_boundary_note']='Add the changed flush to both sides:7191736+172=1908B, cap1916B. The existing shared CRC assembly/table is unchanged and already linked by E1; no extra table allocation.'
 r['resource_only_candidates']={n:dict(resources=resources(paths[n]),two_phase_timing_run=False) for n in ('722A','722B')}
 r['whole_boundary_gate']=r['same_boundary_ledger']['722C']['whole_B']<=r['same_boundary_cap_B']
 assert r['whole_boundary_gate']
 r['board']='707D and existing65816/SDC unchanged; FIT/STA inherited from analysis/bg707-verification.json. No new externalIO/physicalFPS claim.'
 r['complete_CPU_frames']=106
 r['tools']={p.name:sha(p) for p in Path('tools').glob('*722*.py')}
 a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
 print('722 finalized; selected',r['selected'])

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
