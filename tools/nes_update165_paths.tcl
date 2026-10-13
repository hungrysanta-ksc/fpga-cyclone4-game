# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set regs [get_registers {*|loader|terminal *|control|offset_*command}]
if {[get_collection_size $regs]!=3} {error "Expected terminal and two command-kind registers"}
set r [open update165-registers.txt w]
foreach_in_collection reg $regs {puts $r [get_node_info -name $reg]}
close $r
set r [open update165-state-registers.txt w]
foreach_in_collection reg [get_registers {*|loader|state*}] {puts $r [get_node_info -name $reg]}
close $r
set f [open update165-paths.tsv w]
puts $f "corner\tgroup\tkind\tfrom\tto\tslack"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach {group from to} {
  capture {*|control|byte_count*} {*|control|command*}
  address {*|control|offset_*command} {*|control|pending_causes*}
  counter {*|loader|terminal} {*|loader|loaded_bytes*}
  error {*|loader|state*} {*|loader|error_code*}
  begin {*|control|load_begin} {*|loader|state*}
  fault {*|boot|check_failed} {*|loader|state*}
 } {
  foreach kind {setup hold} {
   set paths [get_timing_paths -$kind -from [get_registers $from] -to [get_registers $to] -npaths 1]
   if {[get_collection_size $paths]!=1} {error "Missing $group $kind path"}
   foreach_in_collection path $paths {puts $f "$corner\t$group\t$kind\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"}
   report_timing -$kind -from [get_registers $from] -to [get_registers $to] -npaths 19 -detail full_path -file update165-$i-$group-$kind.rpt
  }
 }
 incr i
}
close $f
delete_timing_netlist
project_close
