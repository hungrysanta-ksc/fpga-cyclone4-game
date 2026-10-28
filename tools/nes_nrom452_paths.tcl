package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set src [get_registers {*|loader|phase*}]
set dst [get_registers {*|loader|loaded_bytes*}]
puts "NROM452 src=[get_collection_size $src] dst=[get_collection_size $dst]"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 report_timing -setup -from $src -to $dst -npaths 20 -detail full_path -file "phase452-$i.rpt"
 set paths [get_timing_paths -setup -from $src -to $dst -npaths 1]
 foreach_in_collection p $paths {puts "NROM452 corner=$corner slack=[get_path_info -slack $p] delay=[get_path_info -data_delay $p]"}
 incr i
}
project_close
