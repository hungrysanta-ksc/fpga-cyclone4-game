# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set f [open timing134.tsv w]
puts $f "corner\tgroup\ttype\tclock\tfrom\tto\tslack"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach type {setup hold} {
  set clock_index 0
  foreach_in_collection c [get_clocks *] {
   set cname [get_clock_info -name $c]
   foreach_in_collection p [get_timing_paths -$type -from_clock $c -to_clock $c -npaths 1] {
    puts $f "$corner\tsame_clock\t$type\t$cname\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -slack $p]"
   }
   report_timing -$type -from_clock $c -to_clock $c -npaths 3 -detail full_path -file same134-$corner-$type-$clock_index.rpt
   incr clock_index
  }
  foreach_in_collection p [get_timing_paths -$type -npaths 1] {
   puts $f "$corner\traw_all\t$type\tall\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -slack $p]"
  }
  report_timing -$type -npaths 8 -detail full_path -file raw134-$corner-$type.rpt
 }
}
close $f
report_ucp -file unconstrained134.rpt
delete_timing_netlist
project_close
