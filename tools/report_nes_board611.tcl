package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
if {[file exists cdc611.sdc]} {source cdc611.sdc}
set f [open paths611.tsv w]
puts $f "corner\tcheck\tslack\tfrom\tto\tfrom_clock\tto_clock"
set sf [open second-paths611.tsv w]
puts $sf "corner\tcheck\tslack\tfrom\tto"
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 set first [get_registers -nowarn {*|rearm|up_dst[0] *|rearm|up_src[0]}]
 set second [get_registers -nowarn {*|rearm|up_dst[1] *|rearm|up_src[1]}]
 if {[get_collection_size $first] && [get_collection_size $second]} {
  foreach k {setup hold} {
   foreach_in_collection p [get_timing_paths -$k -from $first -to $second -npaths 10] {
    puts $sf [join [list $c $k [get_path_info -slack $p] [get_node_info -name [get_path_info -from $p]] [get_node_info -name [get_path_info -to $p]]] "\t"]
   }
  }
 }
 foreach k {setup hold recovery removal} {
  foreach_in_collection p [get_timing_paths -$k -npaths 30 -nworst 3] {
   if {[catch {get_clock_info -name [get_path_info -from_clock $p]} fc]} {set fc "n/a"}
   if {[catch {get_clock_info -name [get_path_info -to_clock $p]} tc]} {set tc "n/a"}
   puts $f [join [list $c $k [get_path_info -slack $p] [get_node_info -name [get_path_info -from $p]] [get_node_info -name [get_path_info -to $p]] $fc $tc] "\t"]
  }
 }
}
close $f
close $sf
report_timing -setup -npaths 10 -detail full_path -file setup611.rpt
report_timing -recovery -npaths 10 -detail full_path -file recovery611.rpt
report_timing -setup -from [get_registers {*|rearm|up_dst[0] *|rearm|up_src[0]}] -to [get_registers {*|rearm|up_dst[1] *|rearm|up_src[1]}] -npaths 10 -file second611.rpt
report_timing -hold -from [get_registers {*|rearm|up_dst[0] *|rearm|up_src[0]}] -to [get_registers {*|rearm|up_dst[1] *|rearm|up_src[1]}] -npaths 10 -append -file second611.rpt
delete_timing_netlist
project_close
