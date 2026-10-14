# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set f [open timer175-paths.tsv w]
puts $f "corner\tgroup\tfrom\tto\tslack"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach {label src dst} {
  timer {*|control|load_begin} {*|loader|remaining*}
  counter {*|boot|check_failed} {*|loader|loaded_bytes*}
 } {
  set from [get_registers $src]
  set to [get_registers $dst]
  set paths [get_timing_paths -setup -from $from -to $to -npaths 1]
  if {[get_collection_size $paths]!=1} {error "Missing $label path"}
  foreach_in_collection p $paths {puts $f "$corner\t$label\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -slack $p]"}
  report_timing -setup -from $from -to $to -npaths 1 -detail full_path -file timer175-$i-$label.rpt
 }
 incr i
}
close $f
delete_timing_netlist
project_close
