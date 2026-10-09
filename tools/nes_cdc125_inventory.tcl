# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open live
create_timing_netlist
read_sdc
set out [open inventory125.tsv w]
puts $out "corner\tfrom\tto\tfrom_clock\tto_clock\tdelay\tslack\tskew\trelationship"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach_in_collection a [get_clocks *] {
  foreach_in_collection b [get_clocks *] {
   if {[get_clock_info -name $a] eq [get_clock_info -name $b]} {continue}
   set paths [get_timing_paths -setup -from_clock $a -to_clock $b -npaths 10000 -nworst 1000]
   if {[get_collection_size $paths]>=10000} {error "Inventory limit reached"}
   foreach_in_collection p $paths {
    puts $out "$corner\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_clock_info -name $a]\t[get_clock_info -name $b]\t[get_path_info -data_delay $p]\t[get_path_info -slack $p]\t[get_path_info -clock_skew $p]\t[get_path_info -clock_relationship $p]"
   }
  }
 }
}
close $out
delete_timing_netlist
project_close
