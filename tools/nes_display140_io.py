# SPDX-License-Identifier: MIT
"""Bound FPGA pad routing on reused140 DB. PCB delay remains an explicit assumption."""
from pathlib import Path
import argparse,csv,json,shutil,subprocess
from nes_spi_boot import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['sta','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--reuse-table',type=Path)
 a=p.parse_args();o=a.out;assert not o.exists();shutil.copytree(a.sta,o)
 script=r'''package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
# Analysis-only broad bounds expose pad routes, without making a full IO signoff.
set_max_delay 1000 -from [get_ports {ROM_DATA* SPI_* SNES_ADDR_IN* SNES_READ_IN SNES_WRITE_IN SNES_ROMSEL_IN SNES_DATA*}] -to [all_registers]
set_max_delay 1000 -from [all_registers] -to [get_ports {ROM_* SPI_MISO MCU_RDY SNES_DATA* SNES_DATABUS*}]
set f [open io140.tsv w]
puts $f "corner\tgroup\tfrom\tto\tdelay\tslack"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach group {input output raw_release} {
  if {$group eq "input"} {
   set paths [get_timing_paths -setup -from [get_ports {ROM_DATA* SPI_* SNES_ADDR_IN* SNES_READ_IN SNES_WRITE_IN SNES_ROMSEL_IN SNES_DATA*}] -to [all_registers] -npaths 100000 -nworst 1000]
  } elseif {$group eq "output"} {
   set paths [get_timing_paths -setup -from [all_registers] -to [get_ports {ROM_* SPI_MISO MCU_RDY SNES_DATA* SNES_DATABUS*}] -npaths 100000 -nworst 1000]
  }
  if {$group eq "raw_release"} {
   set_max_delay 1000 -from [get_ports {SNES_ADDR_IN* SNES_READ_IN SNES_WRITE_IN SNES_ROMSEL_IN}] -to [get_ports {SNES_DATA* SNES_DATABUS*}]
   update_timing_netlist
   set paths [get_timing_paths -setup -from [get_ports {SNES_ADDR_IN* SNES_READ_IN SNES_WRITE_IN SNES_ROMSEL_IN}] -to [get_ports {SNES_DATA* SNES_DATABUS*}] -npaths 100000 -nworst 1000]
  }
  if {[get_collection_size $paths]==0 || [get_collection_size $paths]>=100000} {error "Empty or truncated IO inventory"}
  foreach_in_collection path $paths {
   puts $f "$corner\t$group\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -data_delay $path]\t[get_path_info -slack $path]"
  }
 }
}
close $f
delete_timing_netlist
project_close
'''
 (o/'io140.tcl').write_text(script,encoding='utf8',newline='\n')
 if a.reuse_table:
  assert (a.reuse_table.parent/'io140.tcl').read_text()==script
  shutil.copy2(a.reuse_table,o/'io140.tsv');shutil.copy2(a.reuse_table.parent/'io140.log',o/'io140.log')
 else:
  with (o/'io140.log').open('wb') as f:r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t','io140.tcl'],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=600)
  assert r.returncode==0
 rows=list(csv.DictReader((o/'io140.tsv').open(),delimiter='\t'))
 din=max(float(x['delay']) for x in rows if x['from'].startswith('ROM_DATA['))
 # Only reader address/CE/OE change for each RUN read. Loader write-data/
 # direction and ownership gates are stable before RUN under133 lifecycle.
 dout=max(float(x['delay']) for x in rows if ':reader|' in x['from'] and x['to'].startswith(('ROM_ADDR[','ROM_1CE','ROM_2CE','ROM_OE')))
 allout=max(float(x['delay']) for x in rows if x['to'].startswith('ROM_'))
 spi=max(float(x['delay']) for x in rows if x['to']=='SPI_MISO' or x['from'].startswith('SPI_'))
 local=list(csv.DictReader((o/'local-reset140.tsv').open(),delimiter='\t'))
 chains=list(csv.DictReader((o/'chains140.tsv').open(),delimiter='\t'))
 resetends={x[k] for x in chains if x['kind']=='release' for k in ['first','second']}
 negative=[x for x in local if float(x['slack'])<0];assert negative and all(x['to'] in resetends for x in negative)
 downstream=[x for x in local if x['to'] not in resetends];assert min(float(x['slack']) for x in downstream)>0
 # Conservative allowance2ns for receiving setup+clock uncertainty and2ns total PCB flight.
 # Board flight is not measured: positive result is conditional, not electrical approval.
 margin=16*5.952-70-dout-din-2-2
 assert margin>0 and spi<1000
 snes_in=max(float(x['delay']) for x in rows if x['group']=='input' and x['from'].startswith('SNES_'))
 snes_out=max(float(x['delay']) for x in rows if x['group']=='output' and x['to'].startswith('SNES_'))
 raw=max(float(x['delay']) for x in rows if x['group']=='raw_release')
 # Synthetic137 reads sample at160ns. Eight host periods conservatively cover
 # stable sampling, stage response and registered output; not a measured SNES bound.
 envelope=8*11.904+snes_in+snes_out+4+2
 assert envelope<160
 summary=dict(passed=True,snes_input_max_ns=snes_in,snes_output_max_ns=snes_out,snes_raw_release_max_ns=raw,snes_sample_envelope_ns=round(envelope,3),snes_test_sample_ns=160,snes_io_measured=False,rows=len(rows),psram_input_max_ns=din,psram_output_max_ns=dout,spi_route_max_ns=spi,psram_read_window_ns=16*5.952,psram_access_ns=70,setup_uncertainty_allowance_ns=2,pcb_roundtrip_assumed_ns=2,conditional_read_margin_ns=round(margin,3),reset_rows=len(local),reset_negative_rows=len(negative),negative_only_release_async_inputs=True,downstream_reset_min_ns=min(float(x['slack']) for x in downstream),normal_trial_only=True,new_fit=False,full_io_signoff=False,board_delay_measured=False,mtbf_calculated=False)
 (o/'result.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8');shutil.copy2(__file__,o/'executed-io140.py');print(json.dumps(summary))
if __name__=='__main__':main()
