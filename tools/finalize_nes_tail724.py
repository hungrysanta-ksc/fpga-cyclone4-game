"""Bind724 whole-link resources, two-phase replay and explicit/inherited guards."""
import argparse,json
from pathlib import Path
from nes_raw506 import sha
from analyze_nes_rows713 import resources
from nes_schedule492 import funcs

def run(a):
 r=json.loads((a.probe/'schedule02.json').read_text());r['guards']={}
 for name,path in [('handoff',a.probe/'guards01.json'),('normal_handoff',a.probe/'normal-guards01.json'),
  ('CRC16',a.probe/'crc02.json'),('DMA_gate',a.probe/'gate02.json'),('admission',a.probe/'deadline02.json'),
  ('normal_menu',a.probe/'normal-menu02.json'),('bulk_policy',a.probe/'tail02.json'),('plan',a.probe/'ownership02.json'),
  ('credit',a.probe/'credit02.json'),('runtime',a.probe/'runtime02.json'),('menu',a.probe/'menu02.json'),
  ('STOP',a.temp/'nes-tail724-stop01/result.json'),('inherited_slots',a.probe.parent/'nes-supply720/lazy01.json'),
  ('inherited_BG_CRC8',a.probe.parent/'nes-supply723/guards03.json'),
  ('inherited_same_65816_exit',a.temp/'nes-idle718-exit01/result.json')]:
  g=json.loads(path.read_text());r['guards'][name]=dict(SHA256=sha(path),result=g)
  if 'passed' in g:assert g['passed'],name
  if 'firmware' in g and not name.startswith('inherited_'):
   assert g['firmware']==r['resources']['normal' if name.startswith('normal_') else 'long']['firmware'],name
  if name=='bulk_policy':assert g['variants']['candidate']['firmware']==r['resources']['long']['firmware']
 for phase in r['phases'].values():
  for label in ('original','previous','candidate'):
   phase[label]['details']={g:{k:v for k,v in d.items() if k in ('previous_reveal','interval','early_DMA','relative_ms','BG_ROM_reads','map_packet_B','marks','next_budget721')} for g,d in phase[label]['details'].items()}
  phase['input_borrow']={g:dict(calls=len(xs),duration_ms=sum(x['duration_ms'] for x in xs),checked_blocks=sum(x['checked_blocks'] for x in xs),DMA_notices=sum(len(x['DMA_notices']) for x in xs)) for g,xs in phase['input_borrow'].items()}
 r['same_boundary_ledger']=json.loads((a.probe/'resources01.json').read_text())
 names=('resident_plan213','finish_bg549','status','nes_wire723_crc8','poll','flush','send','wait634','packet_wire','nes_sink212_seal')
 for label,src in [('723',a.probe.parent/'nes-supply723/normal03/src'),('724A',a.probe/'normal01/src'),('724B',a.probe/'normal02/src'),('longB',a.probe/'arm02/src')]:
  v=resources(src);extra={n:size for n,_,size,*_ in funcs(src/'obj-nes-100/sd2snes.elf') if n in names}
  assert r['same_boundary_ledger'][label]==dict(resources=v,extras=extra,whole_B=v['boundary_B']+sum(extra.values()))
 r['same_boundary_cap_B']=4700;r['whole_boundary_gate']=r['same_boundary_ledger']['724B']['whole_B']<=4700
 r['selected']=r['selected'] and r['whole_boundary_gate']
 r['board']='707D/65816/SDC unchanged; existing whole Lite FIT/STA only. No new physical menu/FPS/IO signoff.'
 r['complete_CPU_frames']=106
 r['analysis_correction']='schedule01 compared ROM-window IDs relative to previous display; a 0.70ms display shift crossed a window edge and hid the BG miss. schedule02 compares actual first-to-last BG service windows (0->1); no target or replay changed.'
 r['tools']={p.name:sha(p) for p in Path('tools').glob('*724*.py')}
 a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print('724 selected',r['selected'])

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
