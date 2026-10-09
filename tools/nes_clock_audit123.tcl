# SPDX-License-Identifier: MIT
# Read-only audit of the same fitted123 DB. No timing exceptions are added.
package require ::quartus::sta
project_open live
create_timing_netlist
read_sdc
set f [open clock-pairs123.tsv w]
puts $f "corner\ttype\tfrom_clock\tto_clock\tfrom\tto\tslack\tdata_delay"
set cf [open clocks123.tsv w]
puts $cf "name\tperiod"
foreach_in_collection c [get_clocks *] {puts $cf "[get_clock_info -name $c]\t[get_clock_info -period $c]"}
close $cf
set index 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach_in_collection a [get_clocks *] {
  foreach_in_collection b [get_clocks *] {
   foreach type {setup hold recovery removal} {
    set paths [get_timing_paths -$type -from_clock $a -to_clock $b -npaths 1]
    foreach_in_collection path $paths {
     puts $f "$corner\t$type\t[get_clock_info -name $a]\t[get_clock_info -name $b]\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]\t[get_path_info -data_delay $path]"
     report_timing -$type -from_clock $a -to_clock $b -npaths 4 -detail full_path -file "path123-$index.rpt"
     incr index
    }
   }
  }
 }
}
close $f
report_exceptions -file exceptions123.rpt
report_ucp -file unconstrained123.rpt
delete_timing_netlist
project_close
