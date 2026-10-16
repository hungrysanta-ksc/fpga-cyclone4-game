# SPDX-License-Identifier: MIT
# All-corner inventory, exact topology. No exception changes/signoff implied.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
update_timing_netlist
set f [open topology206.tsv w]
puts $f "first\tfanout"
foreach_in_collection r [get_registers *] {
 set n [get_node_info -name $r]
 if {![string match *direct_path* $n] && ![string match *content_lifetime* $n]} {continue}
 if {![regexp {(epoch_meta\[[0-9]+\]|(req_sync|ack_sync|up_src|up_dst|n_to_h|h_to_n|errors_h)\[0\])$} $n]} {continue}
 set fs [get_fanouts [get_registers $n]]
 if {[get_collection_size $fs]==0} {error "Missing first-stage fanout: $n"}
 foreach_in_collection t $fs {puts $f "$n\t[get_node_info -name $t]"}
}
close $f
set f [open inventory206.tsv w]
puts $f "corner\tkind\tfrom_clock\tto_clock\tfrom\tto\tdelay\tslack"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach kind {setup hold recovery removal} {
  foreach_in_collection a [get_clocks *] {
   foreach_in_collection b [get_clocks *] {
    if {[get_clock_info -name $a] eq [get_clock_info -name $b]} {continue}
    set paths [get_timing_paths -$kind -from_clock $a -to_clock $b -npaths 100000 -nworst 10000]
    if {[get_collection_size $paths]>=100000} {error "CDC inventory truncated"}
    foreach_in_collection p $paths {
     puts $f "$corner\t$kind\t[get_clock_info -name $a]\t[get_clock_info -name $b]\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -data_delay $p]\t[get_path_info -slack $p]"
    }
   }
  }
 }
}
close $f
report_clock_transfers -setup -file transfers206.rpt
delete_timing_netlist
project_close
