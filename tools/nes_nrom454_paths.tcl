package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set s [get_registers {*|loader|loaded_bytes*}]
set t [get_registers {*|control|raw_causes*}]
puts "NROM454 src=[get_collection_size $s] dst=[get_collection_size $t]"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner;update_timing_netlist
 set paths [get_timing_paths -setup -from $s -to $t -npaths 1]
 foreach_in_collection p $paths {puts "NROM454 corner=$corner slack=[get_path_info -slack $p] delay=[get_path_info -data_delay $p] from=[get_node_info -name [get_path_info -from $p]] to=[get_node_info -name [get_path_info -to $p]]"}
}
project_close
