# SPDX-License-Identifier: MIT
# Run only on an isolated COPY. Post-map topology is not routed timing approval.
package require ::quartus::sta
project_open board
create_timing_netlist -post_map
read_sdc
update_timing_netlist
set f [open registers181.tsv w]
puts $f "name"
foreach_in_collection r [get_registers *] {puts $f [get_node_info -name $r]}
close $f
set f [open inventory181.tsv w]
puts $f "kind\tfrom_clock\tto_clock\tfrom\tto\tdelay\tslack"
foreach kind {setup hold recovery removal} {
 foreach_in_collection a [get_clocks *] {
  foreach_in_collection b [get_clocks *] {
   if {[get_clock_info -name $a] eq [get_clock_info -name $b]} {continue}
   set paths [get_timing_paths -$kind -from_clock $a -to_clock $b -npaths 100000 -nworst 10000]
   if {[get_collection_size $paths]>=100000} {error "CDC inventory truncated"}
   foreach_in_collection p $paths {
    puts $f "$kind\t[get_clock_info -name $a]\t[get_clock_info -name $b]\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -data_delay $p]\t[get_path_info -slack $p]"
   }
  }
 }
}
close $f
report_clock_transfers -setup -file transfers181.rpt
delete_timing_netlist
project_close
