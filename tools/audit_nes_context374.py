# SPDX-License-Identifier: MIT
"""Constrained RTL address audit for host-context replacement;no new port/savings."""
import argparse,json,csv,collections
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--run',type=Path);a=p.parse_args();d=BASE/'probes/nes-dual373/map03';v=(d/'nes_validator278.sv').read_text();j=(ROOT/'src/fpga/nes_dual373/nes_joint257.sv').read_text()
 for marker in ('cursor<=512','cursor==677?10\'d768:cursor+1\'b1','cursor==1023','cursor==165','cursor==421','unit359>=1328','unit359>=2048','state<=V_CLEARALL','assign init278=initialized&&!reset&&!fault'):
  assert marker in v,marker
 assert 'always @(posedge host_clk)begin bq<=memory[ram_b_addr];if(ram_b_we&&!fault)memory[ram_b_addr]<=ram_b_w;end' in j
 assert 'aq<=source_shadow373[ram_a_addr[8:0]]' in j
 sets={
  'received_coverage':set(range(512,678))|set(range(768,1024)),
  'persistent_validity':set(range(166))|set(range(256,422)),
  'CRC_banks':set(range(448,512)),
  'H2_and_display':set(range(680,716)),
 }
 used=set().union(*sets.values());free=set(range(1024))-used
 candidates=set(range(716,768));assert len(candidates)==52 and candidates<=free and len(free)==170
 # Current values,cached scopes and namespace state are NOT free to merge.
 context=[('active_record',16),('flow_byte_progress',9),('flow_flags',2),('plan_wire_progress',6),('SPI_request_and_CRC',9)]
 assert sum(n for _,n in context)==42
 trace=None
 if a.run:
  path=a.run/'joint-events.csv';rows=list(csv.reader(path.read_text().splitlines()));starts={};reads=[int(x[-1]) for x in rows if x[0]=='read336'];overlap=collections.Counter();gaps=[];prior=None
  for x in rows:
   if x[0]=='read336':
    key=(x[1],x[2]);t=int(x[-1])
    if prior and prior[0]==key:gaps.append(t-prior[1])
    prior=(key,t)
   if x[0]=='ARM_wire_start334':starts[(x[1],x[2])]=int(x[4])
   if x[0]=='arm267' and (x[1],x[2]) in starts:
    start=starts[(x[1],x[2])];end=int(x[4]);n=sum(start<=t<=end for t in reads)
    if n:overlap[int(x[2])]+=n
  trace=dict(input=str(path),sha256=sha(path),minimum_observed_read_period_ps=min(gaps),approximately_host_clocks=round(min(gaps)/11904),read_bytes_during_command_windows=dict(overlap),WCET=False,
   constraint='42B context cannot be fetched serially for every observed31clock DMA read;retain a read-critical cache/pending capture and prove arbitration deadlines. No new scheduler measured.')
 result=dict(stage=374,passed=True,kind='Constrained static audit,not new RAM port implementation/whole coverage or WCET proof',
  trace=trace,phase_RAM_bytes=1024,source_shadow_bytes=512,existing_RAM_port='one host read/write port;source NES access moved to separate shadow373',
  postinit_legal_region_bytes={k:len(x) for k,x in sets.items()},postinit_used_bytes=len(used),unused_total_bytes=len(free),
  contiguous_context_candidate=[716,767],candidate_bytes=52,minimum_partial_context=context,minimum_partial_context_bytes=42,headroom_bytes=10,
  initialization='V_CLEARALL touches all1024 bytes;new A port must remain disabled until init278,reset/STOP cancels authority.',
  frame_clear='V_CLEARFRAME512..677 then768..1023;V_RAWINVALID148..165/404..421,so52B remains untouched after initialization.',
  bounds='Coverage addresses assume existing accepted-unit<1328/nonmap or<2048/map and existing final-check cursor0..165/255 guards;not an unconstrained all-state theorem.',
  retained_FF='SPI shift/synchronizers,immutable response snapshots/CRC8,queue credit/history,token/serial burn history,physical read capture and independent fault state.',
  required_work='Add host-clock context A port/owner arbiter and schedule SPI ingress vs SNES read/private completion;replace old states/registers/address muxes,not add a shadow. Charge fetch/store deadlines and CDC/fullMAP.',
  actual_port_added=False,actual_logic_deleted=0,time_credit_ms=0,area_credit_comb=0,
  inputs={str(d/'nes_validator278.sv'):sha(d/'nes_validator278.sv'),str(ROOT/'src/fpga/nes_dual373/nes_joint257.sv'):sha(ROOT/'src/fpga/nes_dual373/nes_joint257.sv')})
 a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps({k:result[k] for k in ('candidate_bytes','minimum_partial_context_bytes','headroom_bytes','actual_port_added')}))
if __name__=='__main__':main()
