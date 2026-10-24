# SPDX-License-Identifier: MIT
"""NES341 structural budget and finite allocator-frontier model; no new RTL/M4 run."""
import json
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha

def main():
 pins={}
 def read(p):
  pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
 def js(p):return json.loads(read(p))
 prior={n:js(ROOT/f'analysis/{n}-verification.json') for n in ('ingress338','structure339','hybrid340')}
 checked={}
 for a in prior.values():
  assert a['passed']
  for p,h in a['pins'].items():assert sha(Path(p))==h,p;checked[p]=h
 d=BASE/'probes/nes-ingress338/window03'
 for n in ('nes_resident211.c','nes_planner285.c','order247.h','nes_mux260.sv','nes_core257.sv','nes_plan_batch206.sv'):read(d/n)
 # Existing allocator: used slot is immutable; any unused lower slot may emit
 # later (retained miss or eviction). A data-independent ordered prefix must
 # stay strictly below the first unused slot. Hits/duplicates emit nothing.
 cases=safe=unsafe=0
 for mask in range(256):
  used={i+1 for i in range(8) if mask>>i&1};future=set(range(1,9))-used
  frontier=min(future,default=9)
  for k in used:
   certified=k<frontier
   preserves_all=all(k<later for later in future)
   assert certified==preserves_all
   cases+=1;safe+=certified;unsafe+=not certified
 assert not (5<min({1,2,3,4,6,7,8})) # first chosen slot alone is not a proof
 # Decode the actual first committed E9, not its unavailable emission order.
 arm=js(d/'arm907.json');p=next(bytes.fromhex(t['tx']) for t in arm['transfers'] if t['tx'].startswith('e9'))
 assert len(p)==46 and p[3]==6
 at=4;keys=[]
 for _ in range(p[3]):
  b=p[at:];kind=b[0]&3;n=(7 if b[0]==128 else 8 if b[0]==129 else 3) if b[0]&128 else 16+2*b[1].bit_count()
  off=3 if b[0]&128 else 4
  keys.append(0 if kind==2 else 65535 if kind>2 else 1024*kind+int.from_bytes(b[off:off+2],'little'));at+=n
 assert keys==sorted(keys)
 model=prior['structure339'];base=prior['ingress338'];old=model['rows'][2]
 prefix=.008+18*8/2625000*1000
 # Actual340 206 wire / one bank; old338 floor from independently pinned339.
 floor340=206*8/2625000*1000+.008*2-.004190476190476
 budgets={}
 for name in ('fixed01','window03'):
  c=model['constraints'][name];close=c['previous_close_available_ms']
  budgets[name]=dict(close_ms=close,baseline_nonwire_room_ms=close-old['reference_commit_floor_ms']-prefix,actual340_wire_nonwire_room_ms=close-floor340-prefix,post_ROM_reduction_ms=c['post_ROM_floor_gap_ms'],required_preROM_advance_ms=c['required_preROM_advance_with_3p180_tail_ms'])
 caps=model['area_caps'];assert sum(caps.values())+10950==15253
 out=dict(stage=341,passed=True,selected_RTL=338,selected_ARM=336,new_RTL=False,new_ARM=False,new_MAP=False,new_measured_gain_ms=0,new_comb_gain=0,
  evidence_rehashed=len(checked),frontier_model=dict(slots=8,cases=cases,safe=safe,unsafe=unsafe,actual_first_packet_keys=keys,actual_frontier_ready_time_ms=None,scope='Finite allocator abstraction, NOT actual M4 timing or universal allocator proof. Pending prefix sorted; future used duplicates do not emit. Capacity reservations and STOP lifecycle need actual implementation tests.'),
  time_budgets=budgets,baseline_whole=base['whole'],comb_deficit=1866,area_current=model['area_current'],area_caps=caps,whole_cap=15253,margin=155,net_reduction_required=2021,
  nonwire_cap_ms=dict(source=.35,ARM_decode=.10,BG_prepare_frontier=.30,plan_refill=.15,IRQ_poll_CDC=.10),
  alternative_wire_models=model['aggregates'],max_uniform_greedy_regression_B=max(x['delta'] for x in model['aggregates']['greedy']['regressions']),
  uniform_greedy_extra_wire_ms=max(x['delta'] for x in model['aggregates']['greedy']['regressions'])*8/2625000*1000,
  rejected_raw_source_wire_floor_ms=4910*8/2625000*1000,
  actual340_wire_commit_floor_ms=floor340,prefix_ms=prefix,pins=pins)
 assert sum(out['nonwire_cap_ms'].values())==1.0
 read(ROOT/'tools/analyze_nes_frontier341.py');out['pins']=pins
 (ROOT/'analysis/frontier341-verification.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')
 print(json.dumps({k:v for k,v in out.items() if k not in ('pins','alternative_wire_models')},indent=2))
if __name__=='__main__':main()
