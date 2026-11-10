"""Explain same-work tail and ACK-phase uncertainty without fitting constants.

Window clocks are actual65816 replay clocks. Last-output-return is an upper
bound on ARM's final-ACK timestamp (includes history commit), not that timestamp.
"""
import argparse,json
from pathlib import Path
from analyze_nes_output615 import read,sha,ms,csv_groups,packets

def audit(folder):
 rows=csv_groups(folder/'window.csv');commands=packets(folder);events=read(folder/'events.json');result={}
 for g in (908,911,934,940,943,*range(951,958)):
  cs=commands[g];loads=[x for x in rows[g] if x['event']=='load'];acks=[x for x in rows[g] if x['event']=='ack']
  assert len(cs)==len(loads)==len(acks)
  i=max(i for i,(h,t,push) in enumerate(cs) if h[1]==2)
  prev=next(x for x in rows[g-1] if x['event']=='reveal' and x['op']==3)
  prev_ack=next(x for x in rows[g-1] if x['event']=='ack' and x['op']==3)
  prev_arm=next(x for x in events if x['event']=='output_return531' and x['generation']==g-1)
  seal=next(x for x in loads if x['op']==3)
  tail=[dict(op=h[0],section=h[1],payload_B=len(h)-16,expanded_B=int.from_bytes(h[14:16],'little'),SPI_E1_B=len(h)+3) for h,t,push in cs[i+1:]]
  result[g]=dict(previous_reveal=prev,previous_CPU_ACK=prev_ack,previous_ARM_return=prev_arm,
   previous_ACK_transport_and_history_ms=ms(prev_arm['clock']-prev_ack['clock']),
   last_map_published=cs[i][2],last_map_load=loads[i],last_map_ACK=acks[i],SEAL=seal,
   after_map_ack_to_SEAL_ms=ms(seal['clock']-acks[i]['clock']),
   previous_reveal_to_map_ACK_ms=ms(acks[i]['clock']-prev['clock']),
   tail=tail,tail_E1_wire_B=sum(x['SPI_E1_B'] for x in tail),
   tail_bulk_packets=sum(x['op']==7 for x in tail))
 return dict(frames=result,pins={n:sha(folder/n) for n in ('window.csv','packets.jsonl','events.json')})

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('temp','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();r=dict(scope=__doc__,original717={ph:audit(a.temp/f'nes-tail717-bounded{ph}') for ph in (1,2)})
 for ph in (1,2):
  d=r['original717'][ph]['frames'];assert d[911]['tail']==d[951]['tail']
 r['same_911_951_tail']=True
 if all((a.temp/f'nes-deadline719-a{ph}/joint.json').exists() for ph in (1,2)):
  r['candidate719']={ph:audit(a.temp/f'nes-deadline719-a{ph}') for ph in (1,2)}
 r['not_WCET_proof']='8ms is a replay admission allowance; ACK phase/IRQ/ROM/queue vary. No current beam or reserved SEAL slot is transmitted by E0.'
 a.out.write_text(json.dumps(r,indent=2)+'\n');print('PASS719 same911/951 tail; timing/phase audit saved')
