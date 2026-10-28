# SPDX-License-Identifier: MIT
# Measurement only: do not modify the inherited board constraints.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set src [get_registers {*|loader|phase*}]
set dst [get_registers {*|loader|loaded_bytes*}]
if {[get_collection_size $src] == 0 || [get_collection_size $dst] == 0} {error "missing phase or byte-count register"}
set f [open nrom421-loader-paths.tsv w]
puts $f "corner\tfrom\tto\tdelay\tslack"
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 set paths [get_timing_paths -setup -from $src -to $dst -npaths 10000 -nworst 1000]
 if {[get_collection_size $paths] == 0 || [get_collection_size $paths] >= 10000} {error "missing or truncated paths"}
 foreach_in_collection p $paths {
  puts $f "$c\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -data_delay $p]\t[get_path_info -slack $p]"
 }
}
close $f
delete_timing_netlist
project_close
