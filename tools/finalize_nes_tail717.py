"""Bind717 target cost, observer equivalence, causal ledger and safety evidence."""
import argparse,json
from pathlib import Path
from nes_raw506 import sha
from analyze_nes_output615 import ms

def run(a):
 r=json.loads((a.probe/'schedule01.json').read_text());assert not r['selected']
 r['guards']={}
 for name,p in [('slots',a.probe/'guards01.json'),('policy',a.probe/'policy05.json'),('plan',a.probe/'plan01.json'),
  ('runtime',a.probe/'runtime01.json'),('menu',a.probe/'menu01.json'),('STOP',a.temp/'nes-tail717-stop01/result.json'),
  ('exit',a.temp/'nes-tail717-exit01/result.json'),('search_binding',a.probe/'search-plan-bind01.json')]:
  r['guards'][name]=dict(SHA256=sha(p),result=json.loads(p.read_text()))
 search=json.loads((a.probe/'search02.json').read_text());r['search_profile']=search
 r['causal_ledger']={}
 for ph,p in r['phases'].items():
  r['causal_ledger'][ph]={}
  for label in ('original','B','candidate'):
   data=p[label];out={}
   for g in ('951','954'):
    d=data['details'][g];prev=d['previous_reveal'];tile=max((x for x in d['packets'] if x['op']==7),key=lambda x:x['ack'])
    out[g]=dict(early_DMA=d['early_DMA'],marks=d['marks'],
     last_tile=dict(section=tile['section'],offset=tile['offset'],bytes=tile['expanded_B'],
      relative_ms={k:ms(tile[k]-prev) for k in ('prepared','start','push','load','ack')},
      ready_to_SPI_ms=tile['ready_to_SPI_ms'],SPI_ms=tile['SPI_ms'],queue_ms=tile['queue_ms'],consumer_ms=tile['consumer_ms']),
     relative_ms=d['relative_ms'])
   r['causal_ledger'][ph][label]=out
 r['search_ceiling_ms']={str(x['generation']):dict(prefix_instructions=sum(z['instructions'] for z in x['search_before_last_BG'].values()) if x['search_before_last_BG'] else None,
   prefix_ms=sum(z['instructions'] for z in x['search_before_last_BG'].values())*2/84000 if x['search_before_last_BG'] else None,
   all_search_ms=sum(z['instructions'] for z in x['search'].values())*2/84000) for x in search['rows'] if x['generation'] in (951,954,955,957)}
 r['observer_scope']='673 declared payload ranges unchanged; excluded prior no-op metadata writes. Original716B106frames must match exact clocks/bytes/instructions. Initial original observer fault and rejected dispatcher diagnostics retained, not performance data.'
 # Full packet/CPU rows stay in the hash-pinned raw archive; keep public
 # decision evidence compact and avoid duplicating the three full schedules.
 for phase in r['phases'].values():
  for label in ('original','B','candidate'):
   for detail in phase[label]['details'].values():
    detail.pop('packets',None);detail.pop('DMA_events',None)
 r['next']='Keep selected707D/originalARM/65816. Preserve716B calculation gain. Confirm bounded input work can lend idle map DMA opportunity using actual E0 progress after checked map retirement; no fixed delay or relaxed public line. Search deletion alone has insufficient954 ROM-window budget. Normal Flash still8Bover; no installer.'
 r['tools']={p.name:sha(p) for p in Path('tools').glob('*717*.py')}
 a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
 print('717 evidence finalized; selection false')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
