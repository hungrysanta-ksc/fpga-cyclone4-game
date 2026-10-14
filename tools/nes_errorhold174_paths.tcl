# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set f [open errorhold174-paths.tsv w]
puts $f "corner\tkind\tfrom\tto\tslack"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach kind {setup hold} {
  set from [get_registers {*|control|check_busy}]
  set to [get_registers {*|control|error_code*}]
  set paths [get_timing_paths -$kind -from $from -to $to -npaths 1]
  if {[get_collection_size $paths]!=1} {error "Missing error hold $kind"}
  foreach_in_collection p $paths {puts $f "$corner\t$kind\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -slack $p]"}
  report_timing -$kind -from $from -to $to -npaths 4 -detail full_path -file errorhold174-$i-$kind.rpt
 }
 incr i
}
close $f
delete_timing_netlist
project_close
