# SPDX-License-Identifier: MIT
# Inventory only: unchanged inherited exceptions, no new CDC waiver.
package require ::quartus::sta
project_open board
foreach view {implementation nominal} {
 create_timing_netlist
 if {$view eq "nominal"} {read_sdc nominal204.sdc} else {read_sdc}
 set f [open $view-paths204.tsv w]
 puts $f "corner\tfrom_clock\tto_clock\tkind\tfrom\tto\tslack\tdelay"
 set i 0
 foreach corner [get_available_operating_conditions] {
  set_operating_conditions $corner
  update_timing_netlist
  foreach_in_collection a [get_clocks *] {
   foreach_in_collection b [get_clocks *] {
    foreach kind {setup hold} {
     foreach_in_collection p [get_timing_paths -$kind -from_clock $a -to_clock $b -npaths 10] {
      puts $f "$corner\t[get_clock_info -name $a]\t[get_clock_info -name $b]\t$kind\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -slack $p]\t[get_path_info -data_delay $p]"
     }
    }
   }
  }
  report_timing -setup -npaths 20 -detail full_path -file $view-$i-setup204.rpt
  report_timing -hold -npaths 20 -detail full_path -file $view-$i-hold204.rpt
  incr i
 }
 close $f
 report_ucp -file $view-unconstrained204.rpt
 delete_timing_netlist
}
project_close
