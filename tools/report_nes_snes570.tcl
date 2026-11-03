# SPDX-License-Identifier: MIT
# Diagnostic output-leg inventory only. The fitted project's constraints
# and its original unconstrained-path counts remain the release criterion.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
create_clock -name io570 -period 11.904
set pins [get_ports {SNES_DATABUS_OE SNES_DATABUS_DIR SNES_DATA[*]}]
if {[get_collection_size $pins]!=10} {error "SNES output port inventory"}
set_output_delay -clock io570 -max 0 $pins
set_output_delay -clock io570 -min 0 $pins
set reg [get_registers -nowarn {*|nes_plan_batch206:transport|nes_domain_reset124:hrelease|release_reset*}]
set host [get_clocks {*|pll1|clk[0]}]
if {[get_collection_size $host]!=1} {error "host clock"}
set f [open snes570.tsv w]
puts $f "corner\tleg\tfrom\tto\tdelay"
proc emit570 {f corner leg from to} {
 if {![get_collection_size $from]} {return}
 foreach_in_collection p [get_timing_paths -from $from -to $to -setup -npaths 1] {
  puts $f [join [list $corner $leg [get_node_info -name [get_path_info -from $p]] [get_node_info -name [get_path_info -to $p]] [get_path_info -data_delay $p]] "\t"]
 }
}
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach_in_collection pin $pins {
  emit570 $f $c host $host $pin
  emit570 $f $c plan_release $reg $pin
 }
}
close $f
delete_timing_netlist
project_close
