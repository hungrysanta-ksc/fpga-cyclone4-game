# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set regs [get_registers {*|control|approved_pulse*}]
if {[get_collection_size $regs]!=6} {error "Expected six independently registered command pulses"}
set r [open commandpulse165-registers.txt w]
foreach_in_collection reg $regs {puts $r [get_node_info -name $reg]}
close $r
set f [open commandpulse165-paths.tsv w]
puts $f "corner\tgroup\tkind\tfrom\tto\tslack"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach {group from to} {
  failure {*|boot|check_failed} {*|control|load_valid}
  length {*|loader|loaded_bytes*} {*|control|pending_causes*}
  decode {*|control|pending_command*} {*|control|approved_pulse*}
  response {*|control|check_request_tag*} {*|control|load_begin}
  stop {*|control|stop} {*|loader|state*}
 } {
  foreach kind {setup hold} {
   set paths [get_timing_paths -$kind -from [get_registers $from] -to [get_registers $to] -npaths 1]
   if {[get_collection_size $paths]!=1} {error "Missing $group $kind path"}
   foreach_in_collection path $paths {puts $f "$corner\t$group\t$kind\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"}
   report_timing -$kind -from [get_registers $from] -to [get_registers $to] -npaths 19 -detail full_path -file commandpulse165-$i-$group-$kind.rpt
  }
 }
 incr i
}
close $f
delete_timing_netlist
project_close
