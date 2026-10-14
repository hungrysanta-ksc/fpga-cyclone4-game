# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set f [open ready175-paths.tsv w]
puts $f "corner\ttarget\tpaths\tworst_setup"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 set from [get_registers {*|loader|release_reset[1]}]
 set to [get_registers {*|control|snapshot[40]}]
 if {[get_collection_size $from]!=1 || [get_collection_size $to]!=1} {error "READY175 missing exact registers"}
 set paths [get_timing_paths -setup -from $from -to $to -npaths 1]
 set slack none
 foreach_in_collection p $paths {set slack [get_path_info -slack $p]}
 puts $f "$corner\trelease_to_snapshot40\t[get_collection_size $paths]\t$slack"
 report_timing -setup -to $to -npaths 5 -detail full_path -file ready175-$i-snapshot40.rpt
 incr i
}
close $f
delete_timing_netlist
project_close
