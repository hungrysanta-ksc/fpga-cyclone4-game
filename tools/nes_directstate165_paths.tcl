# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set f [open directstate165-registers.tsv w]
puts $f "group\tname"
foreach {group pattern} {
 phase {*|loader|phase*}
 oldstate {*|loader|state*}
 capture {*|reader|capture_low *|reader|capture_high}
} {
 foreach_in_collection reg [get_registers $pattern] {puts $f "$group\t[get_node_info -name $reg]"}
}
close $f
set f [open directstate165-paths.tsv w]
puts $f "corner\tgroup\tkind\tfrom\tto\tslack"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach {group from to} {
  state {*|loader|phase*} {*|loader|phase*}
  error {*|loader|phase*} {*|loader|error_code*}
  begin {*|control|load_begin} {*|loader|phase*}
  fault {*|boot|check_failed} {*|loader|phase*}
  reader {*|reader|capture_low *|reader|capture_high} {*|reader|data_hold*}
  prediction {*|reader|remaining* *|reader|read_last *|reader|state*} {*|reader|capture_low *|reader|capture_high}
  command {*|control|byte_count*} {*|control|command*}
  address {*|control|offset_*command} {*|control|pending_causes*}
  counter {*|loader|terminal} {*|loader|loaded_bytes*}
 } {
  foreach kind {setup hold} {
   set paths [get_timing_paths -$kind -from [get_registers $from] -to [get_registers $to] -npaths 1]
   if {[get_collection_size $paths]!=1} {error "Missing $group $kind path"}
   foreach_in_collection path $paths {puts $f "$corner\t$group\t$kind\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"}
   report_timing -$kind -from [get_registers $from] -to [get_registers $to] -npaths 9 -detail full_path -file directstate165-$i-$group-$kind.rpt
  }
 }
 incr i
}
close $f
delete_timing_netlist
project_close
