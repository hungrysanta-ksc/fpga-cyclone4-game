# SPDX-License-Identifier: MIT
"""Pin actual RAM ports and a whole-cost ceiling; no claimed RTL deletion."""
import argparse,json
from pathlib import Path
from nes_delta231 import BASE,sha
from analyze_nes_hint367 import hierarchy

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 d=BASE/'probes/nes-source368/map01';pins={}
 def read(name):
  f=d/name;pins[str(f)]=sha(f);return f.read_text(encoding='utf-8-sig')
 source=read('nes_transport257.sv');queue=read('nes_queue260.sv')
 joint=read('nes_joint257.sv');plan=read('nes_plan_batch206.sv')
 tile=read('nes_source_tile192.sv')
 assert 'assign plan_ready=ready_internal&&!fault&&!hint_active361;' in tile
 assert '.plan_valid(plan_valid&&!fault&&!hint_active361)' in tile
 assert '.request(hint_active361?hint_request361:tile_request)' in tile
 assert 'memory[0:511]' in source and 'always @(posedge src_clk)if(byte_valid&&byte_ready)' in source
 assert 'always @(posedge host_clk)read_byte<=memory[' in source
 assert 'buffer[0:1023]' in queue and 'expected_address313<472' in queue
 assert '{1\'b1,retired[0],' in queue
 assert 'always @(posedge clk)if(write312)buffer[' in queue
 assert 'memory[0:1023]' in joint and 'always @(posedge clk)begin aq<=' in joint
 assert 'always @(posedge host_clk)begin bq<=' in joint
 assert 'payload[0:1023]' in plan and 'always @(posedge host_clk)if(write_valid&&write_ready)' in plan
 assert 'always @(posedge nes_clk)data<=payload[' in plan
 cost=hierarchy(d);names=list(cost);self_total=sum(x['comb_self'] for x in cost.values())
 assert self_total==5840
 retain=cost['nes_core257:encoder']['comb_self']+cost['nes_validator278:validator']['comb_self']
 control_pool=self_total-retain;reserve_target=2445
 ports=[dict(name='source immutable blocks',bytes=512,A='NES write',B='host read',lifetime='Source BLOCKEND/pop/commit are distinct from display ACK.'),
  dict(name='expected plus output queue',bytes=1024,A='host E1 write',B='host packet read or expected read/write',expected_bytes=472,packet_slots=[512,768],lifetime='Expected must remain independent; packet storage is two256B slots,not a free1KiB.'),
  dict(name='phase source/validator RAM',bytes=1024,A='NES source',B='host validator',lifetime='Existing phase ownership and cross-clock grant/STOP must remain.'),
  dict(name='plan payload',bytes=1024,A='host write',B='NES read',lifetime='BG partial end,final end and consumption/retire are distinct.')]
 result=dict(passed=True,new_RTL=False,new_MAP=False,deletion_credit_comb=0,ports=ports,hierarchy=cost,
  disjoint_self_total=self_total,retained_codec_and_checker_scenario=retain,remaining_control_pool=control_pool,
  required_net_with155reserve=reserve_target,replacement_control_ceiling=control_pool-reserve_target,
  hint_plan_gate='While hint_active361,all actual tile plan acceptance is blocked,including zero. Cache request/reply routing also follows that owner. Compare a drained/request-owner handoff,not simply removal of the gate.',
  budget_scope='Scenario only: retain current codec/checker self cost and replace all other listed self logic. The1003comb ceiling is necessary under that scenario,not a proven implementation or FIT guarantee.',
  candidate='Only compare a broad common host record/port-progress executor after including source/output lease ownership,independent expected lifetime,host R/W arbitration,plan CDC and STOP drain. Do not mux RAM clocks or count a standalone RAM merge as a logic saving.',pins=pins)
 assert result['replacement_control_ceiling']==1003
 pins[str(Path(__file__).resolve())]=sha(Path(__file__))
 assert not a.out.exists();a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(passed=True,control_pool=control_pool,replacement_ceiling=1003,deletion_credit_comb=0)))
if __name__=='__main__':main()
