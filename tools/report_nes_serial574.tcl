# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set prefix {*|nes_source_epoch207:content_lifetime|}
proc reg {suffix} {
 global prefix
 set r [get_registers ${prefix}${suffix}]
 if {[get_collection_size $r]!=1} {error "missing or nonunique register $suffix"}
 return $r
}
set data0 [reg {data_nes[0]}]
set data1 [reg {data_nes[1]}]
set request0 [reg {request_nes[0]}]
set request1 [reg {request_nes[1]}]
set request2 [reg {request_nes[2]}]
set ack0 [reg {ack_mem[0]}]
set ack1 [reg {ack_mem[1]}]
set source [reg {tx_shift[0]}]
set req [reg request]
set ack [reg ack]
set out [open serial574-paths.tsv w]
puts $out "corner\tcut\tcheck\tslack\tdata_delay\tfrom\tto"
set paths [list [list data_first $source $data0] [list request_first $req $request0] [list ack_first $ack $ack0] \
 [list data_settle $data0 $data1] [list request_settle $request0 $request1] \
 [list request_extra $request1 $request2] [list ack_settle $ack0 $ack1]]
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach cut $paths {
  lassign $cut name from to
  foreach kind {setup hold} {
   set p [get_timing_paths -$kind -from $from -to $to -npaths 1]
   if {![get_collection_size $p]} {error "missing path $name"}
   foreach_in_collection x $p {
    puts $out [join [list $c $name $kind [get_path_info -slack $x] [get_path_info -data_delay $x] [get_node_info -name [get_path_info -from $x]] [get_node_info -name [get_path_info -to $x]]] "\t"]
   }
  }
 }
}
close $out
delete_timing_netlist
project_close
