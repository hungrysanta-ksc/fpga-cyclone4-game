# SPDX-License-Identifier: MIT
# Exact nominal clocks on the existing routed database; no exceptions.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set fault [get_registers {*|loader|fault}]
set causes [get_registers {*|control|pending_causes*}]
if {[get_collection_size $fault]!=1 || [get_collection_size $causes]!=5} {error "Missing loader fault or command cause registers"}
set f [open eligibility165-paths.tsv w]
puts $f "corner\tfrom\tto\tslack"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 set paths [get_timing_paths -setup -from $fault -to $causes -npaths 1]
 if {[get_collection_size $paths]!=1} {error "Missing fault-to-cause path"}
 foreach_in_collection path $paths {
  puts $f "$corner\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"
 }
 report_timing -setup -from $fault -to $causes -npaths 3 -detail full_path -file eligibility165-$i-fault.rpt
 incr i
}
close $f
delete_timing_netlist
project_close
