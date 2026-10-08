# SPDX-License-Identifier: MIT
"""Enumerate all unwaived inter-clock paths and fitted constant memory pins."""
from pathlib import Path
import argparse,csv,json,shutil
from nes_spi_boot import run,put,sha

TCL='''package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc audit.sdc
set f [open crossings.tsv w]
puts $f "corner\ttype\tfrom\tto"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach direction {forward reverse} {
  if {$direction eq "forward"} {set a snes_ref;set b board8} else {set a board8;set b snes_ref}
  foreach type {setup hold recovery removal} {
   foreach_in_collection path [get_timing_paths -$type -from_clock [get_clocks $a] -to_clock [get_clocks $b] -npaths 0] {
    puts $f "$corner\t$type\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]"
   }
  }
 }
}
close $f
report_timing -setup -from [get_registers {*observe|ref_sync[0]}] -to [get_registers {*observe|ref_sync[1]}] -detail full_path -file second-stage.rpt
report_ucp -file unwaived-unconstrained.rpt
delete_timing_netlist
project_close
'''

def main():
 p=argparse.ArgumentParser()
 for n in ['fit','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();fit=a.fit.resolve();out=a.out.resolve();assert str(out).isascii();out.mkdir(parents=True,exist_ok=False)
 result=json.loads((fit/'result.json').read_text());assert result['candidate']=='NES-CLOCK-OBSERVATION-087'
 for n,h in result['sources'].items():assert sha(fit/n)==h,n
 shutil.copytree(fit/'db',out/'db')
 for n in ['board.qsf','board.qpf']:shutil.copy2(fit/n,out/n)
 put(out/'audit.sdc',(fit/'board.sdc').read_text().replace('set_false_path -from $src -to $dst',''))
 put(out/'audit.tcl',TCL);shutil.copy2(__file__,out/'executed-driver.py')
 run([a.quartus_bin/'quartus_sta.exe','-t','audit.tcl'],out,'audit',1200)
 with (out/'crossings.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
 assert len(rows)==6 and len({r['corner'] for r in rows})==3
 for r in rows:assert r['type'] in ['setup','hold'] and r['from'].endswith('|divider[3]') and r['to'].endswith('|ref_sync[0]'),r
 m=(fit/'output_files/board.map.rpt').read_text(encoding='latin1');f=(fit/'output_files/board.fit.rpt').read_text(encoding='latin1')
 high=['ROM_1CE','ROM_2CE','ROM_OE','ROM_WE','ROM_BHE','ROM_BLE','ROM_ZZ','RAM_OE','RAM_WE','SNES_DATABUS_OE']
 disabled=[f'{bus}[{i}]' for bus,bits in [('ROM_DATA',16),('RAM_DATA',8),('SNES_DATA',8)] for i in range(bits)]
 for n in high:assert f'Pin "{n}" is stuck at VCC' in m,n
 for n in disabled:assert f'Pin {n} has a permanently disabled output enable' in f,n
 put(out/'result.json',json.dumps(dict(candidate='NES-CLOCK-OBSERVATION-087',crossings=rows,constant_high=high,output_disabled=disabled,fit_result_sha256=sha(fit/'result.json'),physical_pin_behavior_measured=False,installable=False),indent=2)+'\n')
 print('PASS CF87 routed6 crossings /10 constant inactive controls /32 disabled data pins')

if __name__=='__main__':main()
