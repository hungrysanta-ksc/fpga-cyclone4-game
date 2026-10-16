# SPDX-License-Identifier: MIT
# Measure local reset release to every epoch sampling register, including
# same-clock recovery/removal (not present in the cross-clock inventory).
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
update_timing_netlist
set targets {}
set f [open reset207-topology.tsv w]
puts $f "first\tfanout"
foreach_in_collection r [get_registers *] {
 set n [get_node_info -name $r]
 if {![string match *content_lifetime* $n]} {continue}
 if {[regexp {\|(epoch_meta|epoch_sync|previous)\[[0-9]+\]$} $n]} {lappend targets $n}
 if {![regexp {:(cold_release|release_ready)\|release_reset\[0\]$} $n]} {continue}
 foreach_in_collection t [get_fanouts [get_registers $n]] {puts $f "$n\t[get_node_info -name $t]"}
}
close $f
if {[llength $targets]!=96} {error "Expected exactly96 epoch registers"}
set f [open reset207.tsv w]
puts $f "corner\tkind\tfrom\tto\tdelay\tslack"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach n $targets {
  foreach kind {recovery removal} {
   set paths [get_timing_paths -$kind -to [get_registers $n] -npaths 100 -nworst 100]
   if {[get_collection_size $paths]==0 || [get_collection_size $paths]>=100} {error "Missing/truncated reset path: $n $kind"}
   foreach_in_collection p $paths {
    puts $f "$corner\t$kind\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -data_delay $p]\t[get_path_info -slack $p]"
   }
  }
 }
}
close $f
delete_timing_netlist
project_close
