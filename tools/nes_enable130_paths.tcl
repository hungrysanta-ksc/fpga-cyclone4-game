# SPDX-License-Identifier: MIT
# Read-only state register port and same-domain timing inventory.
package require ::quartus::sta
project_open live
create_timing_netlist
read_sdc
set regs [get_registers [list {*nes_rom_loader:loader|state*} {*nes_rom_loader:loader|remaining*}]]
if {[get_collection_size $regs]!=16} {error "Unexpected loader state/counter register inventory"}
set f [open state130-edges.tsv w]
puts $f "register\tsource\tdestination"
foreach_in_collection r $regs {
 foreach e [get_register_info -synch_edges $r] {
  puts $f "[get_node_info -name $r]\t[get_node_info -name [get_edge_info -src $e]]\t[get_node_info -name [get_edge_info -dst $e]]"
 }
}
close $f
set f [open state130-timing.tsv w]
puts $f "corner\ttype\tfrom\tto\tslack"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach type {setup hold} {
  set ps [get_timing_paths -$type -to $regs -npaths 10000 -nworst 1000]
  if {[get_collection_size $ps]>=10000} {error "Truncated state paths"}
  foreach_in_collection p $ps {
   puts $f "$corner\t$type\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -slack $p]"
  }
  report_timing -$type -to $regs -npaths 8 -detail full_path -file state130-$corner-$type.rpt
 }
}
close $f
delete_timing_netlist
project_close
