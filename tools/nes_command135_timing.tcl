# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set f [open timing134.tsv w]
puts $f "corner\tgroup\ttype\tclock\tfrom\tto\tslack"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach type {setup hold} {
  set clock_index 0
  foreach_in_collection c [get_clocks *] {
   set cname [get_clock_info -name $c]
   foreach_in_collection p [get_timing_paths -$type -from_clock $c -to_clock $c -npaths 1] {
    puts $f "$corner\tsame_clock\t$type\t$cname\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -slack $p]"
   }
   report_timing -$type -from_clock $c -to_clock $c -npaths 3 -detail full_path -file same134-$corner-$type-$clock_index.rpt
   incr clock_index
  }
  foreach_in_collection p [get_timing_paths -$type -npaths 1] {
   puts $f "$corner\traw_all\t$type\tall\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -slack $p]"
  }
  report_timing -$type -npaths 8 -detail full_path -file raw134-$corner-$type.rpt
 }
}
close $f
report_ucp -file unconstrained134.rpt
set f [open registers135.tsv w]
puts $f "register\tsource\tdestination"
set count 0
foreach_in_collection r [get_registers {*nes_rom_loader:loader|loaded_bytes*}] {
 incr count
 foreach edge [get_register_info -synch_edges $r] {
  puts $f "[get_node_info -name $r]\t[get_node_info -name [get_edge_info -src $edge]]\t[get_node_info -name [get_edge_info -dst $edge]]"
 }
}
if {$count!=17} {error "Expected17 loaded byte registers"}
close $f
set f [open targeted135.tsv w]
puts $f "corner\tgroup\tfrom\tto\tslack"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach group {pending_causes check_failed loaded_bytes} pattern {{*nes_rom_spi_check:control|pending_causes*} {*nes_rom_boot:boot|check_failed} {*nes_rom_loader:loader|loaded_bytes*}} {
  set rs [get_registers $pattern]
  if {[get_collection_size $rs]==0} {error "Missing target $group"}
  foreach_in_collection p [get_timing_paths -setup -to $rs -npaths 1] {
   puts $f "$corner\t$group\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -slack $p]"
  }
 }
}
close $f
delete_timing_netlist
project_close
