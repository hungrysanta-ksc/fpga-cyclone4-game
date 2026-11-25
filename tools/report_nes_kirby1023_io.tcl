# Measure routed delays without changing the fitted project or its SDC.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set address [get_ports {ROM_ADDR*}]
set active [get_ports {ROM_1CE ROM_2CE ROM_OE}]
set capture [get_registers {*reader|data_hold* *reader|bg_hold*}]
set inputs [get_ports {ROM_DATA*}]
set_max_delay 1000 -from [all_registers] -to $address
set_max_delay 1000 -from $inputs -to $capture
set f [open kirby1023-io.tsv w]
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach {name from to} [list address [all_registers] $address upper [all_registers] [get_ports {ROM_ADDR[16]}] active [all_registers] $active capture $inputs $capture] {
  set paths [get_timing_paths -setup -from $from -to $to -npaths 256 -nworst 1]
  if {![get_collection_size $paths]} {error "missing path $name"}
  set longest 0
  foreach_in_collection p $paths {
   set longest [expr {max($longest,[get_path_info -data_delay $p])}]
  }
  puts $f "$c\t$name\t$longest"
 }
}
close $f
delete_timing_netlist
project_close
