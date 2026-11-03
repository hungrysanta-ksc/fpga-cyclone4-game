# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set out [open epoch568.tsv w]
puts $out "corner\tpath\tbit\tfrom\tto\tslack\tdata_delay"
proc row {f c tag bit paths} {
 foreach_in_collection p $paths {
  puts $f [join [list $c $tag $bit [get_node_info -name [get_path_info -from $p]] [get_node_info -name [get_path_info -to $p]] [get_path_info -slack $p] [get_path_info -data_delay $p]] "\t"]
 }
}
set origin {*|nes_source_epoch207:content_lifetime|}
set meta [get_registers ${origin}epoch_meta*]
set sync [get_registers ${origin}epoch_sync*]
if {[get_collection_size $meta]!=32 || [get_collection_size $sync]!=32} {error "missing epoch bits"}
set fail [get_registers {*|nes_rom_boot:boot|check_failed}]
set endreg [get_registers -nowarn {*|nes_rom_loader:loader|reject_state[2]}]
set loader [get_registers {*|nes_rom_loader:loader|*}]
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach_in_collection target $meta {
  set name [get_node_info -name $target]
  if {![regexp {epoch_meta\[([0-9]+)\]} $name -> bit]} {error $name}
  row $out $c input $bit [get_timing_paths -setup -to $target -npaths 1]
 }
 foreach_in_collection target $sync {
  set name [get_node_info -name $target]
  if {![regexp {epoch_sync\[([0-9]+)\]} $name -> bit]} {error $name}
  row $out $c sync $bit [get_timing_paths -setup -from $meta -to $target -npaths 1]
 }
 row $out $c nes_hold -1 [get_timing_paths -hold -to_clock [get_clocks nes] -npaths 1]
 row $out $c blocked -1 [get_timing_paths -setup -from $fail -to $loader -npaths 1]
 if {[get_collection_size $endreg]} {
  row $out $c end -1 [get_timing_paths -setup -from $fail -to $endreg -npaths 1]
 }
}
close $out
delete_timing_netlist
project_close
