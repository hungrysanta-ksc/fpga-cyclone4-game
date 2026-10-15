# SPDX-License-Identifier: MIT
# Same post-map netlist, old CDC constraints vs added eight capture constraints.
# Run on the scope COPY, never the selected FIT database.
package require ::quartus::sta
project_open board
foreach view {before after} {
 create_timing_netlist -post_map
 if {$view eq "before"} {read_sdc before181.sdc} else {read_sdc}
 update_timing_netlist
 set f [open scope181-$view.tsv w]
 puts $f "kind\tfrom_clock\tto_clock\tfrom\tto"
 foreach kind {setup hold recovery removal} {
  foreach_in_collection a [get_clocks *] {
   foreach_in_collection b [get_clocks *] {
    if {[get_clock_info -name $a] eq [get_clock_info -name $b]} {continue}
    set paths [get_timing_paths -$kind -from_clock $a -to_clock $b -npaths 100000 -nworst 10000]
    if {[get_collection_size $paths]>=100000} {error "reply scope truncated"}
    foreach_in_collection path $paths {
     puts $f "$kind\t[get_clock_info -name $a]\t[get_clock_info -name $b]\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]"
    }
   }
  }
 }
 close $f
 delete_timing_netlist
}
project_close
