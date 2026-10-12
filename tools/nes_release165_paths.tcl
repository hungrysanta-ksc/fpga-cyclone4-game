# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
set settings [open release165-settings.tsv w]
puts $settings "target\tvalue"
foreach target {core|native_records|dr[0] core|native_records|dr[1] core|native_prepared|sr[0] core|native_prepared|sr[1]} {
 set value [get_instance_assignment -name DONT_MERGE_REGISTER -to $target]
 if {$value ne "ON"} {error "Missing merge protection $target"}
 puts $settings "$target\t$value"
}
close $settings
create_timing_netlist
read_sdc nominal165.sdc
proc exact165 {name} {
 set r [get_registers $name]
 if {[get_collection_size $r]!=1} {error "Missing register $name"}
 return $r
}
set topology [open release165-topology.tsv w]
puts $topology "chain\tstage\tfrom\tto"
foreach {chain stem} {records core|native_records|dr prepared core|native_prepared|sr} {
 foreach bit {0 1} {
  set node [exact165 "$stem\[$bit\]"]
  foreach_in_collection src $node {
   foreach_in_collection dst [get_fanouts $node] {puts $topology "$chain\t$bit\t[get_node_info -name $src]\t[get_node_info -name $dst]"}
  }
 }
}
close $topology
set f [open release165-paths.tsv w]
puts $f "corner\tgroup\tkind\tfrom\tto\tslack"
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach {group stem} {records core|native_records|dr prepared core|native_prepared|sr} {
  foreach kind {setup hold} {
   set paths [get_timing_paths -$kind -from [exact165 "$stem\[0\]"] -to [exact165 "$stem\[1\]"] -npaths 1]
   if {[get_collection_size $paths]!=1} {error "Missing chain path"}
   foreach_in_collection path $paths {puts $f "$corner\t$group\t$kind\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"}
  }
 }
 set args [list -from [exact165 {core|native_records|dr[1]}] -to [get_registers {*|native_spi|held*}]]
 set paths [get_timing_paths -setup {*}$args -npaths 1]
 if {[get_collection_size $paths]!=1} {error "Missing release to SPI held path"}
 foreach_in_collection path $paths {puts $f "$corner\theld\tsetup\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"}
 report_timing -setup {*}$args -npaths 3 -detail full_path -file release165-$i-held.rpt
 incr i
}
close $f
delete_timing_netlist
project_close
