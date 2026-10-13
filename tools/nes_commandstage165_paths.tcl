# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set f [open commandstage165-paths.tsv w]
puts $f "corner\tgroup\tkind\tfrom\tto\tslack"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach {group from to} {
  failure {*|boot|check_failed} {*|control|check_next*}
  length {*|loader|loaded_bytes*} {*|control|pending_causes*}
  decode {*|control|pending_causes*} {*|control|decoded_error*}
  eligibility {*|control|pending_causes*} {*|control|pending_counter_clear}
  stop {*|control|stop} {*|loader|state*}
 } {
  foreach kind {setup hold} {
   set paths [get_timing_paths -$kind -from [get_registers $from] -to [get_registers $to] -npaths 1]
   if {[get_collection_size $paths]!=1} {error "Missing $group $kind path"}
   foreach_in_collection path $paths {puts $f "$corner\t$group\t$kind\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"}
   report_timing -$kind -from [get_registers $from] -to [get_registers $to] -npaths 19 -detail full_path -file commandstage165-$i-$group-$kind.rpt
  }
 }
 incr i
}
close $f
delete_timing_netlist
project_close
