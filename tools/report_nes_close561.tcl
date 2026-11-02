# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set out [open close561-paths.tsv w]
puts $out "corner\tboundary\tcheck\tslack\tfrom\tto"
set mark [get_registers -nowarn {*|nes_tile_bulk206:bulk|announced}]
set inherited [open close561-crossings.tsv w]
puts $inherited "corner\tcheck\tclock\tslack\tfrom\tto"
set bulk [get_registers {*|nes_tile_bulk206:bulk|*}]
set decoder [get_registers {*|nes_plan_batch206:transport|*}]
set tile [get_registers {*|nes_tile205:tile|*}]
set rx [get_registers {*|nes_native_mailbox206:tiles|received*}]
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach_in_collection clk [get_clocks *] {
  set name [get_clock_info -name $clk]
  if {$name eq "nes"} {set kind setup} elseif {[string first {clk[1]} $name]>=0} {set kind recovery} else {continue}
  foreach_in_collection p [get_timing_paths -$kind -to_clock $clk -npaths 1] {
   puts $inherited "$c\t$kind\t$name\t[get_path_info -slack $p]\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]"
  }
 }
 if {[get_collection_size $mark]==0} {continue}
 foreach cut [list [list marker_in -from_clock [get_clocks nes] -to $mark] [list marker_out -from $mark -to_clock [get_clocks nes]] [list decoder -from $bulk -to $decoder] [list tile -from $bulk -to $tile] [list host -from $rx -to $bulk]] {
  foreach check {setup hold} {
   set paths [get_timing_paths -$check {*}[lrange $cut 1 end] -npaths 1]
   foreach_in_collection p $paths {
    puts $out "$c\t[lindex $cut 0]\t$check\t[get_path_info -slack $p]\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]"
   }
  }
 }
}
close $out
close $inherited
delete_timing_netlist
project_close
