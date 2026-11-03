# SPDX-License-Identifier: MIT
# Read-only audit of an existing routed image. No SDC exceptions or new FIT.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set clocks [get_clocks *]
report_clocks -file boundary575-clocks.rpt
report_clock_transfers -setup -file boundary575-transfers.rpt
set f [open boundary575-negative.tsv w]
puts $f "corner\tcheck\tslack\tdata_delay\tfrom_clock\tto_clock\tfrom\tto"
set counts [open boundary575-counts.tsv w]
puts $counts "corner\tcheck\tfrom_clock\tto_clock\tcount"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach kind {setup hold recovery removal} {
  foreach_in_collection src $clocks {
   foreach_in_collection dst $clocks {
    set paths [get_timing_paths -$kind -from_clock $src -to_clock $dst -less_than_slack 0 -npaths 20000 -nworst 1]
    set n [get_collection_size $paths]
    if {$n>=20000} {error "endpoint collection truncated"}
    puts $counts [join [list $corner $kind [get_clock_info -name $src] [get_clock_info -name $dst] $n] "\t"]
    foreach_in_collection p $paths {
     puts $f [join [list $corner $kind [get_path_info -slack $p] [get_path_info -data_delay $p] \
       [get_clock_info -name [get_path_info -from_clock $p]] [get_clock_info -name [get_path_info -to_clock $p]] \
       [get_node_info -name [get_path_info -from $p]] [get_node_info -name [get_path_info -to $p]]] "\t"]
    }
   }
  }
 }
}
close $f
close $counts
delete_timing_netlist
project_close
