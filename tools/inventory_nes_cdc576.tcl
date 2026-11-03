# SPDX-License-Identifier: MIT
# Include positive paths hidden by worst-endpoint-only reporting.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
update_timing_netlist
set out [open cdc576-all.tsv w]
puts $out "check\tfrom_clock\tto_clock\tfrom\tto\tslack\tdata_delay"
foreach_in_collection a [get_clocks *] {
 foreach_in_collection b [get_clocks *] {
  set ac [get_clock_info -name $a]
  set bc [get_clock_info -name $b]
  if {!(($ac eq "nes") != ($bc eq "nes"))} {continue}
  set ps [get_timing_paths -setup -from_clock $a -to_clock $b -npaths 200000 -nworst 10000]
  if {[get_collection_size $ps]>=200000} {error "path inventory truncated"}
  foreach_in_collection p $ps {
   puts $out [join [list setup $ac $bc [get_node_info -name [get_path_info -from $p]] [get_node_info -name [get_path_info -to $p]] [get_path_info -slack $p] [get_path_info -data_delay $p]] "\t"]
  }
 }
}
close $out
delete_timing_netlist
project_close
