# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set origin {*|nes_source_epoch207:content_lifetime|}
set gray [get_registers ${origin}gray\[*\]]
set meta [get_registers ${origin}epoch_meta*]
set sync [get_registers ${origin}epoch_sync*]
foreach regs [list $gray $meta $sync] {
 if {[get_collection_size $regs]!=32} {error "expected 32 physical registers"}
}
set locations [open epoch573-sites.tsv w]
puts $locations "name\tsite"
foreach regs [list $gray $meta $sync] {
 foreach_in_collection r $regs {
  puts $locations "[get_node_info -name $r]\t[get_node_info -location $r]"
 }
}
close $locations
set holds [open epoch573-hold.tsv w]
puts $holds "corner\tto\tfrom\tslack\tdata_delay"
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach targets [list $meta $sync] {
  foreach_in_collection r $targets {
   foreach_in_collection p [get_timing_paths -hold -to $r -npaths 1] {
    puts $holds [join [list $c [get_node_info -name $r] [get_node_info -name [get_path_info -from $p]] [get_path_info -slack $p] [get_path_info -data_delay $p]] "\t"]
   }
  }
 }
 if {[string match "*slow*0mv_0c" $c]} {
  report_timing -setup -npaths 32 -nworst 1 -from $gray -to $meta -detail full_path -file epoch573-input.rpt
  report_timing -setup -npaths 32 -nworst 1 -from $meta -to $sync -detail full_path -file epoch573-sync.rpt
 }
}
close $holds
delete_timing_netlist
project_close
