# SPDX-License-Identifier: MIT
# Observe the new request-tag register on the same routed nominal-clock DB.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set tags [get_registers {*|control|check_request_tag*}]
if {[get_collection_size $tags]!=19} {error "Expected 19 independent CHECK tag bits"}
set f [open tag165-paths.tsv w]
puts $f "corner\tgroup\tfrom\tto\tslack"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach group {capture response} {
  if {$group eq "capture"} {
   set paths [get_timing_paths -setup -to $tags -npaths 1]
  } else {
   set paths [get_timing_paths -setup -from $tags -to [get_registers {*|control|check_next*}] -npaths 1]
  }
  if {[get_collection_size $paths]!=1} {error "Missing tag path $group"}
  foreach_in_collection path $paths {
   puts $f "$corner\t$group\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"
  }
 }
}
close $f
delete_timing_netlist
project_close
