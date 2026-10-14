# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set f [open legality174-registers.tsv w]
puts $f "name"
foreach_in_collection r [get_registers {*|loader|reject_state*}] {puts $f [get_node_info -name $r]}
close $f
set f [open legality174-paths.tsv w]
puts $f "corner\tgroup\tkind\tfrom\tto\tslack"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach {group from to} {
  datafault {*|control|load_valid} {*|loader|fault}
  checkfault {*|boot|check_failed} {*|loader|fault}
  legality {*} {*|loader|reject_state*}
 } {
  foreach kind {setup hold} {
   set paths [get_timing_paths -$kind -from [get_registers $from] -to [get_registers $to] -npaths 1]
   if {[get_collection_size $paths]!=1} {error "Missing $group $kind path"}
   foreach_in_collection path $paths {puts $f "$corner\t$group\t$kind\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"}
   report_timing -$kind -from [get_registers $from] -to [get_registers $to] -npaths 3 -detail full_path -file legality174-$i-$group-$kind.rpt
  }
 }
 incr i
}
close $f
delete_timing_netlist
project_close
