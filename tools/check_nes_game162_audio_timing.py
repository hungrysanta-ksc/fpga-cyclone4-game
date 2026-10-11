# SPDX-License-Identifier: MIT
"""Held audio mailbox and DAC port routing bounds on the selected placement."""
from pathlib import Path
import argparse,csv,json,subprocess
TCL=r'''package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set f [open audio162.tsv w]
puts $f "corner\tgroup\tfrom\tto\tdelay\tslack"
set_max_delay 1000 -from [all_registers] -to [get_ports {DAC_*}]
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach group {data pins} {
  if {$group eq "data"} {
   set paths [get_timing_paths -setup -from [get_registers {*audio*held_sample*}] -to [get_registers {*audio*dac_sample*}] -npaths 100 -nworst 100]
  } else {
   set paths [get_timing_paths -setup -from [all_registers] -to [get_ports {DAC_*}] -npaths 100 -nworst 100]
  }
  if {[get_collection_size $paths]==0 || [get_collection_size $paths]>=100} {error "Empty/truncated $group"}
  foreach_in_collection path $paths {
   puts $f "$corner\t$group\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -data_delay $path]\t[get_path_info -slack $path]"
  }
 }
}
close $f
delete_timing_netlist
project_close
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--fit',type=Path,required=True);p.add_argument('--quartus-bin',type=Path,required=True);a=p.parse_args()
 (a.fit/'audio162.tcl').write_text(TCL)
 with (a.fit/'audio162.log').open('wb') as f:r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t','audio162.tcl'],cwd=a.fit,stdout=f,stderr=subprocess.STDOUT,timeout=180)
 assert r.returncode==0,'audio162.log'
 rows=list(csv.DictReader((a.fit/'audio162.tsv').open(),delimiter='\t'));data=[v for v in rows if v['group']=='data'];pins=[v for v in rows if v['group']=='pins']
 assert len({v['corner'] for v in rows})==3
 for corner in {v['corner'] for v in rows}:
  assert len([v for v in data if v['corner']==corner])==16
  assert {v['to'] for v in pins if v['corner']==corner}=={'DAC_MCLK','DAC_LRCK','DAC_SDOUT'}
 data_max=max(float(v['delay']) for v in data);pin_max=max(float(v['delay']) for v in pins)
 result=dict(passed=data_max<11.904 and pin_max<11.904,mailbox_data_max_ns=data_max,dac_output_max_ns=pin_max,rows=len(rows),data_pairs=16,corners=3,contract='Two receiver synchronizer stages then capture; source holds until returned acknowledgment. Data bound one84MHz period. Pin propagation under one84MHz period; pin waveform matched to existing GBC serializer. Not complete analog DAC/PCB signoff.',mtbf_calculated=False,physical_audio=False)
 (a.fit/'audio162-timing.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed'],result;print(json.dumps(result))
if __name__=='__main__':main()
