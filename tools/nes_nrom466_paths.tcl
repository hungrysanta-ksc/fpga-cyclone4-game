# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set f [open reset466-paths.tsv w]
puts $f "corner\tgroup\tkind\tfrom_clock\tto_clock\tfrom\tto\tdelay\tslack"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach kind {setup hold} {
  foreach_in_collection a [get_clocks *] {
   foreach_in_collection b [get_clocks *] {
    set an [get_clock_info -name $a];set bn [get_clock_info -name $b]
    if {($an eq "nes") != ($bn eq "nes")} {continue}
    foreach_in_collection p [get_timing_paths -$kind -from_clock $a -to_clock $b -npaths 1] {
     puts $f "$corner\trelated\t$kind\t$an\t$bn\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -data_delay $p]\t[get_path_info -slack $p]"
    }
   }
  }
 }
 foreach n {{nes_sink_bridge165:sink|host_ready} {nes_sink_bridge165:sink|idle_ss[0]} {nes_sink_bridge165:sink|idle_ss[1]} {nes_sink_bridge165:sink|idle_write[0]} {nes_sink_bridge165:sink|idle_write[1]}} {
  set regs [get_registers $n]
  if {[get_collection_size $regs]!=1} {error "missing exact sink state $n"}
  foreach kind {recovery removal} {
   foreach_in_collection p [get_timing_paths -$kind -to $regs -npaths 1] {
    puts $f "$corner\tsink\t$kind\t[get_path_info -from_clock $p]\t[get_path_info -to_clock $p]\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -data_delay $p]\t[get_path_info -slack $p]"
   }
  }
 }
}
close $f
report_ucp -file reset466-unconstrained.rpt
project_close
