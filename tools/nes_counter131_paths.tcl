# SPDX-License-Identifier: MIT
# Read-only state register port and same-domain timing inventory.
package require ::quartus::sta
project_open live
create_timing_netlist
read_sdc
set regs [get_registers [list {*nes_rom_loader:loader|state*} {*nes_rom_loader:loader|remaining*}]]
if {[get_collection_size $regs]!=16} {error "Unexpected loader state/counter register inventory"}
set f [open state131-edges.tsv w]
puts $f "register\tsource\tdestination"
foreach_in_collection r $regs {
 foreach e [get_register_info -synch_edges $r] {
  puts $f "[get_node_info -name $r]\t[get_node_info -name [get_edge_info -src $e]]\t[get_node_info -name [get_edge_info -dst $e]]"
 }
}
close $f
set f [open state131-timing.tsv w]
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
  report_timing -$type -to $regs -npaths 8 -detail full_path -file state131-$corner-$type.rpt
 }
}
close $f
set f [open counter131-dependencies.tsv w]
puts $f "corner\tgroup\tpaths\tslack"
set counter [get_registers {*nes_rom_loader:loader|remaining*}]
set counts [get_registers {*nes_rom_loader:loader|loaded_bytes*}]
set failed [get_registers {*nes_rom_boot:boot|check_failed}]
if {[get_collection_size $counter]!=7 || [get_collection_size $counts]!=17 || [get_collection_size $failed]!=1} {error "Unexpected counter source register inventory"}
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach {label sources} [list loaded_count $counts check_failed $failed] {
  set ps [get_timing_paths -setup -from $sources -to $counter -npaths 1]
  set n [get_collection_size $ps]
  if {$n==0} {puts $f "$corner\t$label\t0\t-"}
  foreach_in_collection p $ps {puts $f "$corner\t$label\t$n\t[get_path_info -slack $p]"}
 }
}
close $f
set f [open index131-edges.tsv w]
puts $f "register\tsource\tdestination"
set index_regs [get_registers {*nes_rom_spi_check:control|check_next*}]
if {[get_collection_size $index_regs]!=17} {error "Unexpected CHECK index inventory"}
foreach_in_collection r $index_regs {
 foreach e [get_register_info -synch_edges $r] {
  puts $f "[get_node_info -name $r]\t[get_node_info -name [get_edge_info -src $e]]\t[get_node_info -name [get_edge_info -dst $e]]"
 }
}
close $f
set f [open address131-edges.tsv w]
puts $f "register\tsource\tdestination"
set address_regs [get_registers {*nes_rom_loader:loader|load_address*}]
if {[get_collection_size $address_regs]==0} {error "No loader address registers"}
foreach_in_collection r $address_regs {
 foreach e [get_register_info -synch_edges $r] {
  puts $f "[get_node_info -name $r]\t[get_node_info -name [get_edge_info -src $e]]\t[get_node_info -name [get_edge_info -dst $e]]"
 }
}
close $f
set f [open checked131-edges.tsv w]
puts $f "register\tsource\tdestination"
set checked_regs [get_registers {*nes_rom_spi_check:control|checked_data*}]
if {[get_collection_size $checked_regs]!=8} {error "Unexpected CHECK response data inventory"}
foreach_in_collection r $checked_regs {
 foreach e [get_register_info -synch_edges $r] {
  puts $f "[get_node_info -name $r]\t[get_node_info -name [get_edge_info -src $e]]\t[get_node_info -name [get_edge_info -dst $e]]"
 }
}
close $f
delete_timing_netlist
project_close
