# SPDX-License-Identifier: MIT
"""Generate routed timing reports preserving CDC181 in both timing views.

Unlike the old clocks-only helper, nominal181 keeps the exact CDC exceptions.
All related clock pairs (including different outputs of one PLL) remain checked.
Run only after successful FIT; the output scripts do not run another FIT.
"""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from check_nes_cdc181 import generate

def main():
    p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True)
    a=p.parse_args();d=a.folder
    assert 'Fitter was successful' in (d/'fit.log').read_text(errors='replace')
    m=json.loads((d/'preparation.json').read_bytes())
    for n,h in m['sources'].items():assert sha(d/n)==h,n
    assert not (d/'nominal181.sdc').exists() and not (d/'timing181.tcl').exists()
    s=(d/'board.sdc').read_text();assert s.endswith('\nsource cdc181.sdc\n')
    assert s.count('#156 Implementation budgets')==1
    nominal=s.split('#156 Implementation budgets',1)[0]+'source cdc181.sdc\n'
    (d/'nominal181.sdc').write_text(nominal,encoding='utf8')
    script='''package require ::quartus::sta
project_open board
foreach view {implementation nominal} {
 create_timing_netlist
 if {$view eq "nominal"} {read_sdc nominal181.sdc} else {read_sdc}
 set f [open $view-clocks181.tsv w]
 puts $f "corner\tfrom_clock\tto_clock\tkind\tfrom\tto\tslack\tdelay"
 foreach corner [get_available_operating_conditions] {
  set_operating_conditions $corner
  update_timing_netlist
  foreach_in_collection a [get_clocks *] {
   foreach_in_collection b [get_clocks *] {
    set ca [get_clock_info -name $a];set cb [get_clock_info -name $b]
    if {($ca eq "nes") != ($cb eq "nes")} {continue}
    foreach kind {setup hold} {
     foreach_in_collection p [get_timing_paths -$kind -from_clock $a -to_clock $b -npaths 10] {
      puts $f "$corner\t$ca\t$cb\t$kind\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -slack $p]\t[get_path_info -data_delay $p]"
     }
    }
   }
  }
  report_timing -setup -npaths 10 -detail full_path -file $view-$corner-setup181.rpt
  report_timing -hold -npaths 10 -detail full_path -file $view-$corner-hold181.rpt
 }
 close $f
 report_ucp -file $view-unconstrained181.rpt
 delete_timing_netlist
}
project_close
'''
    (d/'timing181.tcl').write_text(script,encoding='utf8')
    generate(d,False)
    # IO collector keeps its established conditional envelopes, now with the
    # exact new CDC maximum/hold exceptions. Its 1000ns IO bounds are NOT passes.
    io=(ROOT/'tools/nes_boundary165_paths.tcl').read_text().replace('read_sdc nominal165.sdc','read_sdc nominal181.sdc')
    anchor='set paths [get_timing_paths -setup -from [get_registers $from] -to [get_registers $to] -npaths 20000 -nworst 1000]'
    assert io.count(anchor)==1
    io=io.replace(anchor,'''if {$group in {records_req prepared_req}} {
  set paths [get_timing_paths -setup -false_path -from [get_registers $from] -to [get_registers $to] -npaths 20000 -nworst 1000]
 } else {
  set paths [get_timing_paths -setup -from [get_registers $from] -to [get_registers $to] -npaths 20000 -nworst 1000]
 }''')
    (d/'io181.tcl').write_text(io,encoding='utf8')
    print('Generated routed timing/CDC/conditional IO scripts; no FIT or clock relaxation')

if __name__=='__main__':main()
