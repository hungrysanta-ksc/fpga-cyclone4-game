package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set f [open paths612.tsv w]
puts $f "corner\tcheck\tslack\tfrom\tto\tfrom_clock\tto_clock"
set io [open io612.tsv w]
puts $io "corner\tport\tslack\tfrom\tdelay"
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach k {setup hold recovery removal} {
  foreach_in_collection p [get_timing_paths -$k -npaths 30 -nworst 3] {
   if {[catch {get_clock_info -name [get_path_info -from_clock $p]} fc]} {set fc "n/a"}
   if {[catch {get_clock_info -name [get_path_info -to_clock $p]} tc]} {set tc "n/a"}
   puts $f [join [list $c $k [get_path_info -slack $p] [get_node_info -name [get_path_info -from $p]] [get_node_info -name [get_path_info -to $p]] $fc $tc] "\t"]
  }
 }
 foreach pin {ROM_1CE ROM_2CE ROM_OE} {
  foreach_in_collection p [get_timing_paths -setup -to [get_ports $pin] -npaths 1] {
   puts $io [join [list $c $pin [get_path_info -slack $p] [get_node_info -name [get_path_info -from $p]] [get_path_info -data_delay $p]] "\t"]
  }
  report_timing -setup -to [get_ports $pin] -npaths 1 -detail full_path -file "$pin-$c-612.rpt"
 }
 report_timing -setup -npaths 3 -detail full_path -file "setup-$c-612.rpt"
 report_timing -recovery -npaths 3 -detail full_path -file "recovery-$c-612.rpt"
}
close $f
close $io
delete_timing_netlist
project_close
