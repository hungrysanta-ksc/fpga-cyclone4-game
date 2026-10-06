# SPDX-License-Identifier: MIT
# Separate bounded-resolution experiment. Original SDF/notifier failures remain evidence.
import sys,json,re
from pathlib import Path
import nes_h1_sampling_gate as base

def add_model(net,mode):
 nodes=['addr_meta['+str(i)+']' for i in range(24)]+['data_meta['+str(i)+']' for i in range(8)]+['rd_sync[0]','wr_sync[0]','sel_sync[0]']
 lines=[' integer resolved_count=0;integer resolution_fd;', ' initial resolution_fd=$fopen("resolutions.txt","w");']
 for i,name in enumerate(nodes):
  escaped=chr(92)+'boundary|link|transport|frontend|'+name
  assert 'dffeas '+escaped+' (' in net,name
  node='dut.'+escaped+' '
  lines += [f' reg previous_{i}=0,chosen_{i}=0;',
   f' always @(negedge {node}.clk) if(!$isunknown({node}.q)) previous_{i}<={node}.q;',
   f' always @({node}.viol) begin',
   '  #1;',
   f'  if({node}.clrn===1 && $isunknown({node}.q))begin',
   f'   chosen_{i}={node}.sload ? {node}.asdata : {node}.d;']
  if mode=='old':lines += [f'   chosen_{i}=previous_{i};']
  elif mode=='mixed':lines += [f'   if((resolved_count+{i})%2==0)chosen_{i}=previous_{i};']
  lines += [f'   if($isunknown(chosen_{i}))chosen_{i}=previous_{i};',
   f'   $fdisplay(resolution_fd,"%0t {i} {name} %b %b",$time,previous_{i},chosen_{i});resolved_count++;',
   f'   force {node}.q=chosen_{i};',
   f'   @(posedge {node}.clk);#2;release {node}.q;',
   '  end',' end']
 lines += [' final $display("RESOLUTION MODEL applied=%0d",resolved_count);']
 return chr(10).join(lines)

if __name__=='__main__':
 at=sys.argv.index('--resolution');mode=sys.argv[at+1];del sys.argv[at:at+2];assert mode in ('old','new','mixed')
 netlist=Path(sys.argv[sys.argv.index('--netlist')+1]);out=Path(sys.argv[sys.argv.index('--out')+1])
 base.TB=base.TB.replace(' task automatic dump;',add_model(netlist.read_text(),mode)+chr(10)+' task automatic dump;')
 base.main()
 p=out/'result.json';r=json.loads(p.read_text());records=(out/'resolutions.txt').read_text().splitlines()
 r.update(resolution_mode=mode,resolution_events=len(records),timing_notifiers_enabled=True,
  resolution_assumption='Only35 frontend first-stage q outputs may resolve to previous/current binary value1ns after a notifier; force released2ns after next local clock. Floating input fallback=previous. No downstream/ROM/register/event force. Testbench-only assumption, not physical MTBF or timing signoff.',
  original_unresolved_result='044 raw SDF failed126bytes/884violations; preserved separately')
 p.write_text(json.dumps(r,indent=2)+chr(10));print(json.dumps(r,indent=2))
