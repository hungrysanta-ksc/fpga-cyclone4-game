# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set begin_reg [get_registers {*|control|load_begin}]
set states [get_registers {*|loader|state*}]
if {[get_collection_size $begin_reg]!=1 || [get_collection_size $states]<1} {error "Missing loader state path"}
set f [open state165-paths.tsv w]
puts $f "corner\tfrom\tto\tslack"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 set paths [get_timing_paths -setup -from $begin_reg -to $states -npaths 1]
 if {[get_collection_size $paths]!=1} {error "Missing BEGIN to state path"}
 foreach_in_collection path $paths {puts $f "$corner\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"}
 report_timing -setup -from $begin_reg -to $states -npaths 5 -detail full_path -file state165-$i-begin.rpt
 incr i
}
close $f
delete_timing_netlist
project_close
