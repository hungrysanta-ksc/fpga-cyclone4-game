# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set f [open counterpulse167-paths.tsv w]
puts $f "corner\tgroup\tfrom\tto\tslack"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach {group pattern} {check {*|control|check_next*} loaded {*|loader|loaded_bytes*} clear {*|control|pending_counter_clear} increment {*|control|pending_counter_inc}} {
  set paths [get_timing_paths -setup -to [get_registers $pattern] -npaths 1]
  if {[get_collection_size $paths]!=1} {error "Missing $group"}
  foreach_in_collection path $paths {
   puts $f "$corner\t$group\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"
  }
 }
}
close $f
delete_timing_netlist
project_close
