# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set out [open plan569.tsv w]
puts $out "corner\tpath\tcheck\tslack\tdelay\tfrom\tto"
set plan {*|nes_plan_batch206:transport|}
set box "${plan}nes_native_mailbox206:control|"
set held [get_registers ${box}held*]
set saved [get_registers -nowarn ${box}received*]
set fields [get_registers [list ${plan}reader ${plan}batch_length* ${plan}remaining*]]
set inventory [open plan569-registers.tsv w]
puts $inventory "held\tsaved\tfields"
puts $inventory "[get_collection_size $held]\t[get_collection_size $saved]\t[get_collection_size $fields]"
close $inventory
if {[get_collection_size $held]!=16 || [get_collection_size $fields]!=16} {error "descriptor width"}
proc record {file corner name kind args} {
 foreach_in_collection path [get_timing_paths -$kind {*}$args -npaths 1] {
  puts $file [join [list $corner $name $kind [get_path_info -slack $path] [get_path_info -data_delay $path] [get_node_info -name [get_path_info -from $path]] [get_node_info -name [get_path_info -to $path]]] "\t"]
 }
}
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach_in_collection reg $held {
  regexp {held\[([0-9]+)\]$} [get_node_info -name $reg] -> bit
  foreach k {setup hold} {
   if {[get_collection_size $saved]} {record $out $c saved$bit $k -from $reg -to $saved}
   record $out $c direct$bit $k -from $reg -to $fields
  }
 }
 foreach k {hold setup} {record $out $c nes $k -to_clock [get_clocks nes]}
}
close $out
delete_timing_netlist
project_close
