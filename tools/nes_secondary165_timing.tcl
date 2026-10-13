# SPDX-License-Identifier: MIT
# Unchanged implementation SDC. Inventory only, not external IO/CDC approval.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set f [open secondary165-clocks.tsv w]
puts $f "corner\tclock\tkind\tfrom\tto\tslack"
set corner_index 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 set clock_index 0
 foreach_in_collection clock [get_clocks *] {
  foreach kind {setup hold} {
   foreach_in_collection path [get_timing_paths -$kind -from_clock $clock -to_clock $clock -npaths 10] {
    puts $f "$corner\t[get_clock_info -name $clock]\t$kind\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"
   }
   report_timing -$kind -from_clock $clock -to_clock $clock -npaths 5 -detail full_path -file "secondary165-$corner_index-$clock_index-$kind.rpt"
  }
  incr clock_index
 }
 report_timing -setup -npaths 10 -detail full_path -file "secondary165-$corner_index-mixed-setup.rpt"
 incr corner_index
}
close $f
report_ucp -file secondary165-unconstrained.rpt
delete_timing_netlist
project_close
