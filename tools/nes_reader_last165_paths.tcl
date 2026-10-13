# SPDX-License-Identifier: MIT
# Reader terminal register and sample enable on the existing routed database.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set last [get_registers {*|reader|read_last}]
set data [get_registers {*|reader|data_hold*}]
if {[get_collection_size $last]!=1 || [get_collection_size $data]!=8} {error "Missing terminal/data registers"}
set f [open reader-last165-paths.tsv w]
puts $f "corner\tgroup\tfrom\tto\tslack"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach group {terminal sample} {
  if {$group eq "terminal"} {set args [list -to $last]} else {set args [list -from $last -to $data]}
  set paths [get_timing_paths -setup {*}$args -npaths 1]
  if {[get_collection_size $paths]!=1} {error "Missing reader path $group"}
  foreach_in_collection path $paths {
   puts $f "$corner\t$group\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"
  }
  report_timing -setup {*}$args -npaths 3 -detail full_path -file reader-last165-$i-$group.rpt
 }
 incr i
}
close $f
delete_timing_netlist
project_close
