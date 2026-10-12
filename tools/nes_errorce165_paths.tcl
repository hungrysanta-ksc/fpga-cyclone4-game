# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set f [open errorce165-paths.tsv w]
puts $f "corner\tkind\tfrom\tto\tslack"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach kind {setup hold} {
  set from [get_registers {*|loader|state*}]
  set to [get_registers {*|loader|error_code*}]
  set paths [get_timing_paths -$kind -from $from -to $to -npaths 1]
  if {[get_collection_size $paths]!=1} {error "Missing error-code path"}
  foreach_in_collection path $paths {puts $f "$corner\t$kind\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"}
  report_timing -$kind -from $from -to $to -npaths 5 -detail full_path -file errorce165-$i-$kind.rpt
 }
 incr i
}
close $f
delete_timing_netlist
project_close
