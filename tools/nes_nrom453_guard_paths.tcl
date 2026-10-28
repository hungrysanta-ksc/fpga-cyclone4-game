package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set s [get_registers {*|clock_guard|ref_qualified}]
set t [get_registers {*|reader|memory_reset*}]
puts "GUARD453 sources=[get_collection_size $s] targets=[get_collection_size $t]"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner;update_timing_netlist
 foreach kind {setup recovery removal} {
  set paths [get_timing_paths -$kind -from $s -to $t -npaths 10]
  puts "GUARD453 corner=$corner kind=$kind paths=[get_collection_size $paths]"
  foreach_in_collection p $paths {puts "GUARD453 path=$kind slack=[get_path_info -slack $p] from=[get_node_info -name [get_path_info -from $p]] to=[get_node_info -name [get_path_info -to $p]]"}
 }
}
project_close
