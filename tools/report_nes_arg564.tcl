# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set out [open arg564-paths.tsv w]
puts $out "corner\tcut\tcheck\tslack\tfrom\tto"
proc emit {file corner cut kind args} {
 foreach_in_collection p [get_timing_paths -$kind {*}$args -npaths 1] {
  puts $file "$corner\t$cut\t$kind\t[get_path_info -slack $p]\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]"
 }
}
set addr [get_registers {*|nes_rom_spi_check:control|arg[*]}]
set count [get_registers {*|nes_rom_spi_check:control|byte_count*}]
set enable [get_registers -nowarn {*|nes_rom_spi_check:control|arg_write}]
if {[get_collection_size $addr]!=8 || [get_collection_size $count]!=4} {error "unexpected SPI-register inventory"}
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 emit $out $corner old_capture setup -from $count -to $addr
 emit $out $corner OE setup -to [get_ports ROM_OE]
 if {[get_collection_size $enable]} {
  emit $out $corner decode setup -from $count -to $enable
  emit $out $corner write setup -from $enable -to $addr
 }
 foreach_in_collection clk [get_clocks *] {
  set name [get_clock_info -name $clk]
  foreach kind {setup recovery} {emit $out $corner $name $kind -to_clock $clk}
 }
}
close $out
delete_timing_netlist
project_close
