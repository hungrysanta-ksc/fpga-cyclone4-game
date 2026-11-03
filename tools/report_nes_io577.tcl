# SPDX-License-Identifier: MIT
# Existing routed image only. No mutation of release constraints.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set f [open loader577.tsv w]
puts $f "corner\tcheck\tfrom\tto\tslack\tdelay"
set src [get_registers {*|nes_rom_spi_check:control|load_end}]
set dst [get_registers {*|nes_rom_loader:loader|remaining*}]
if {[get_collection_size $src]!=1 || [get_collection_size $dst]!=7} {error "loader endpoint inventory"}
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach k {setup hold} {
  foreach_in_collection p [get_timing_paths -$k -from $src -to $dst -npaths 7 -nworst 1] {
   puts $f [join [list $c $k [get_node_info -name [get_path_info -from $p]] [get_node_info -name [get_path_info -to $p]] [get_path_info -slack $p] [get_path_info -data_delay $p]] "\t"]
  }
 }
 report_timing -setup -from $src -to $dst -npaths 1 -detail full_path -file loader577-$c.rpt
}
close $f
delete_timing_netlist
# IO inventory uses a zero-insertion virtual clock, not an asserted board spec.
create_timing_netlist
read_sdc
create_clock -name io577 -period 381.000
set in [get_ports {SPI_SCK SPI_SS SPI_MOSI SNES_ADDR_IN[*] SNES_READ_IN SNES_WRITE_IN SNES_ROMSEL_IN SNES_DATA[*] ROM_DATA[*]}]
set out [get_ports {SPI_MISO MCU_RDY SNES_DATA[*] SNES_DATABUS_OE SNES_DATABUS_DIR ROM_ADDR[*] ROM_DATA[*] ROM_1CE ROM_2CE ROM_OE ROM_WE ROM_BHE ROM_BLE}]
set_input_delay -clock io577 -max 0 $in
set_output_delay -clock io577 -max 0 $out
set f [open io577.tsv w]
puts $f "corner\tgroup\tfrom\tto\tslack\tlaunch\tlatch\tdelay"
proc emit577 {f c label ps} {
 foreach_in_collection p $ps {
  set r [list $c $label]
  foreach k {-from -to} {lappend r [get_node_info -name [get_path_info $k $p]]}
  foreach k {-slack -launch_time -latch_time -data_delay} {lappend r [get_path_info $k $p]}
  puts $f [join $r "\t"]
 }
}
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach_in_collection pin [get_ports {SPI_MISO MCU_RDY SNES_DATABUS_OE SNES_DATABUS_DIR SNES_DATA[*]}] {
  emit577 $f $c output [get_timing_paths -setup -to $pin -npaths 1]
 }
 foreach_in_collection pin $in {
  emit577 $f $c input [get_timing_paths -setup -from $pin -npaths 1]
 }
 set ld [get_registers {*|nes_rom_loader:loader|*}]
 foreach_in_collection pin [get_ports {ROM_ADDR[*] ROM_DATA[*] ROM_1CE ROM_2CE ROM_OE ROM_WE ROM_BHE ROM_BLE}] {
  emit577 $f $c loader_output [get_timing_paths -setup -from $ld -to $pin -npaths 1]
 }
}
close $f
delete_timing_netlist
project_close
