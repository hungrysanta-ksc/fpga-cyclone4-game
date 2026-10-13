# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set regs [get_registers {*|loader|state*}]
if {[get_collection_size $regs]<1} {error "Missing loader state registers"}
set r [open destination165-registers.txt w]
foreach_in_collection reg $regs {puts $r [get_node_info -name $reg]}
close $r
set f [open destination165-paths.tsv w]
puts $f "corner\tgroup\tkind\tfrom\tto\tslack"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach {group from to} {
  begin {*|control|load_begin} {*|loader|state*}
  fault {*|boot|check_failed} {*|loader|state*}
  timer {*|loader|remaining*} {*|loader|state*}
  error {*|loader|state*} {*|loader|error_code*}
 } {
  foreach kind {setup hold} {
   set paths [get_timing_paths -$kind -from [get_registers $from] -to [get_registers $to] -npaths 1]
   if {[get_collection_size $paths]!=1} {error "Missing $group $kind path"}
   foreach_in_collection path $paths {puts $f "$corner\t$group\t$kind\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"}
   report_timing -$kind -from [get_registers $from] -to [get_registers $to] -npaths 19 -detail full_path -file destination165-$i-$group-$kind.rpt
  }
 }
 incr i
}
close $f
delete_timing_netlist
project_close
