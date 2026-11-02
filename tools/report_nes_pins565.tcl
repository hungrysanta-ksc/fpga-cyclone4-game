# SPDX-License-Identifier: MIT
# Separate inventory on an already fitted board. Ideal external clock has no
# insertion delay. Sum the two FPGA legs at the package pins in the analyzer.
package require ::quartus::sta
project_open board
create_timing_netlist
create_clock -name board8 -period 125 [get_ports CLKIN]
create_clock -name nes -period 45.454 [get_ports SNES_SYSCLK]
derive_pll_clocks
create_clock -name io565 -period 5.952
derive_clock_uncertainty
set output [get_ports {ROM_ADDR* ROM_OE ROM_1CE ROM_2CE}]
set input [get_ports {ROM_DATA*}]
set_output_delay -clock io565 -max 0 $output
set_input_delay -clock io565 -max 0 $input
set reader [get_registers {*|nes_rom_physical:reader|*}]
set active [get_registers {*|nes_rom_physical:reader|reading_active}]
set capture [get_registers {*|nes_rom_physical:reader|data_hold*}]
if {[get_collection_size $active]!=1 || [get_collection_size $capture]!=8 || [get_collection_size $input]!=16} {error "pin register inventory"}
set out [open pins565.tsv w]
puts $out "corner\tleg\tfrom\tto\tslack\tlaunch\tlatch\tdelay"
proc emit {f c leg paths} {
 foreach_in_collection p $paths {
  set r [list $c $leg]
  foreach k {-from -to} {lappend r [get_node_info -name [get_path_info $k $p]]}
  foreach k {-slack -launch_time -latch_time -data_delay} {lappend r [get_path_info $k $p]}
  puts $f [join $r "\t"]
 }
}
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach_in_collection pin $output {
  emit $out $c early [get_timing_paths -setup -from $reader -to $pin -npaths 1]
  emit $out $c active [get_timing_paths -setup -from $active -to $pin -npaths 1]
 }
 foreach_in_collection pin $input {
  emit $out $c data [get_timing_paths -setup -from $pin -to $capture -npaths 1]
 }
}
close $out
delete_timing_netlist
create_timing_netlist
read_sdc
set out [open reset565.tsv w]
puts $out "corner\tcut\tfrom\tto\tslack\tlaunch\tlatch\tdelay"
set core [get_registers {*|nes_domain_reset124:core_release|release_reset*}]
set cancel [get_registers {*|nes_tile_bulk206:bulk|nes_domain_reset124:hcancel|release_reset*}]
if {[get_collection_size $core]==0 || [get_collection_size $cancel]==0} {error "missing reset endpoints"}
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c;update_timing_netlist
 emit $out $c core_cancel [get_timing_paths -recovery -from $core -to $cancel -npaths 1]
 emit $out $c cancel [get_timing_paths -recovery -to $cancel -npaths 1]
}
close $out
delete_timing_netlist
project_close
