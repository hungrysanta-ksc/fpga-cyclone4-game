# SPDX-License-Identifier: MIT
# Same routed database and unchanged SDC; no new timing exceptions.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set f [open check165-paths.tsv w]
puts $f "corner\tgroup\tfrom\tto\tslack"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach group {check loader miso} {
  if {$group eq "check"} {
   set sources [get_registers {*|control|check_next* *|reader|check_response_address*}]
   set targets [get_registers {*|control|*}]
  } elseif {$group eq "loader"} {
   set sources [get_registers {*|boot|check_failed}]
   set targets [get_registers {*|loader|state*}]
  } else {
   set sources [get_registers {*|control|byte_count*}]
   set targets [get_registers {*|control|miso_hold}]
  }
  set paths [get_timing_paths -setup -from $sources -to $targets -npaths 1]
  if {[get_collection_size $paths]!=1} {error "Missing path group $group"}
  foreach_in_collection path $paths {
   puts $f "$corner\t$group\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"
  }
 }
}
close $f
delete_timing_netlist
project_close
