# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set length_reg [get_registers {*|loader|loaded_bytes*}]
set states [get_registers {*|control|pending_counter_clear}]
if {[get_collection_size $length_reg]!=19 || [get_collection_size $states]<1} {error "Missing loader state path"}
set f [open length165-paths.tsv w]
puts $f "corner\tfrom\tto\tslack"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 set paths [get_timing_paths -setup -from $length_reg -to $states -npaths 1]
 if {[get_collection_size $paths]!=1} {error "Missing LENGTH to state path"}
 foreach_in_collection path $paths {puts $f "$corner\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"}
 report_timing -setup -from $length_reg -to $states -npaths 5 -detail full_path -file length165-$i-clear.rpt
 incr i
}
close $f
delete_timing_netlist
project_close
