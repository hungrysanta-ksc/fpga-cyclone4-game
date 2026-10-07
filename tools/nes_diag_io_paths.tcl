# SPDX-License-Identifier: MIT
# Measurement-only clone of routed DB. Zero IO delays expose FPGA-only paths;
# their slack is NOT a board constraint or electrical signoff.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set outputs [get_ports {ROM_ADDR[*] ROM_1CE ROM_2CE ROM_OE ROM_WE ROM_BHE ROM_BLE ROM_DATA[*]}]
set inputs [get_ports {ROM_DATA[*]}]
set_output_delay -clock board8 -max 0 $outputs
set_output_delay -clock board8 -min 0 $outputs
set_input_delay -clock board8 -max 0 $inputs
set_input_delay -clock board8 -min 0 $inputs
set f [open io-paths.tsv w]
puts $f "corner\tanalysis\tdirection\tfrom\tto\tdata_delay\tarrival\tlaunch\trequired\tlatch"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach type {setup hold} {
  foreach dir {out in} {
   if {$dir eq "out"} {
    set paths [get_timing_paths -$type -from_clock board8 -to $outputs -npaths 0 -detail full_path]
   } else {
    set paths [get_timing_paths -$type -from $inputs -to [get_registers {*reader*data_hold*}] -npaths 0 -detail full_path]
   }
   if {[get_collection_size $paths]==0} {error "Missing routed PSRAM paths: $corner/$type/$dir"}
   foreach_in_collection path $paths {
    set from [get_node_info [get_path_info -from $path] -name]
    set to [get_node_info [get_path_info -to $path] -name]
    puts $f "$corner\t$type\t$dir\t$from\t$to\t[get_path_info -data_delay $path]\t[get_path_info -arrival_time $path]\t[get_path_info -launch_time $path]\t[get_path_info -required_time $path]\t[get_path_info -latch_time $path]"
   }
   report_timing -$type -npaths 8 -detail full_path -from [expr {$dir eq "in"?$inputs:[get_registers *]}] -to [expr {$dir eq "out"?$outputs:[get_registers {*reader*data_hold*}]}] -file "io-$dir-$type-$corner.rpt"
  }
 }
}
close $f
delete_timing_netlist
project_close
