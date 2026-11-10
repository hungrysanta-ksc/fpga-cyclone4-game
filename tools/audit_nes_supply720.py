"""Same-work BG deadlines and OBJ capture/bulk ownership, non-additive spans."""
import argparse,json
from pathlib import Path
from analyze_nes_output615 import read,sha,ms,csv_groups,packets

def audit(folder):
 rows=csv_groups(folder/'window.csv');cmds=packets(folder)
 ev=read(folder/'events.json');obj=read(folder/'obj-phases.json');out={}
 for g in (953,956):
  prev=next(x['clock'] for x in rows[g-1] if x['event']=='reveal' and x['op']==3)
  loads=[x for x in rows[g] if x['event']=='load'];acks=[x for x in rows[g] if x['event']=='ack']
  assert len(loads)==len(acks)==len(cmds[g])
  tile=[];maps=[]
  for (h,b,push),lo,ack in zip(cmds[g],loads,acks):
   r=dict(op=h[0],section=h[1],offset=int.from_bytes(h[12:14],'little'),expanded_B=int.from_bytes(h[14:16],'little'),
    push_ms=ms(push-prev),load_ms=ms(lo['clock']-prev),ACK_ms=ms(ack['clock']-prev))
   if h[0]==7:tile.append(r)
   elif h[1]==2:maps.append(r)
  o=obj[str(g)];cache=o['cache611'];calls=[e for e in ev if e['event']=='call673' and e['generation']==g and e['name']=='nes_plan200_emit']
  bykind={k:[e for e in calls if bytes.fromhex(e['plan'])[6]==k] for k in (0,1)}
  out[g]=dict(previous_reveal=prev,tile=tile,maps=maps,
   first_BG_call_ms=ms(bykind[0][0]['clock']-prev),last_BG_call_ms=ms(bykind[0][-1]['clock']-prev),
   first_OBJ_call_ms=ms(bykind[1][0]['clock']-prev),last_OBJ_call_ms=ms(bykind[1][-1]['clock']-prev),
   OBJ_first_plan_ms=ms(min(q['accepted_clock'] for q in o['obj_plans'])-prev),
   OBJ_last_plan_ms=ms(max(q['accepted_clock'] for q in o['obj_plans'])-prev),
   OBJ_first_request_ms=ms(o['first_obj_rom_request']-prev),OBJ_last_response_ms=ms(o['last_obj_rom_response']-prev),
   reads=[dict(kind=q[0],tag=q[1],request_ms=ms(q[2]-prev),grant_ms=ms(q[3]-prev),response_ms=ms(q[4]-prev),source=q[5]) for q in cache],
   read_sources={name:sum(q[0]==1 and q[5]==name for q in cache) for name in {q[5] for q in cache if q[0]==1}},
   SEAL_load_ms=ms(next(x['clock'] for x in loads if x['op']==3)-prev))
 return dict(frames=out,pins={n:sha(folder/n) for n in ('window.csv','packets.jsonl','events.json','obj-phases.json')})

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('temp','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();r=dict(scope=__doc__,not_WCET='Capture-backed OBJ intervals are not external ROM stalls. Request, queue and ARM spans overlap and must not be added.')
 for name,tag in [('previous','nes-deadline719'),('candidate','nes-supply720')]:r[name]={ph:audit(a.temp/f'{tag}-a{ph}') for ph in (1,2)}
 a.out.write_text(json.dumps(r,indent=2)+'\n');print('PASS720 BG/OBJ request, supply and receipt audit')
