# SPDX-License-Identifier: MIT
# Separate ideal IO clock only for path inventory. Keep the release SDC intact.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
create_clock -name io571 -period 11.904
set outputs [get_ports {SNES_DATABUS_OE SNES_DATABUS_DIR SNES_DATA[*]}]
set controls [get_ports {SNES_READ_IN SNES_WRITE_IN SNES_ADDR_IN[*] SNES_ROMSEL_IN}]
if {[get_collection_size $outputs]!=10 || [get_collection_size $controls]!=27} {error "pin count"}
set_input_delay -clock io571 -max 0 $controls
set_input_delay -clock io571 -min 0 $controls
set_output_delay -clock io571 -max 0 $outputs
set_output_delay -clock io571 -min 0 $outputs
set old [get_registers -nowarn {*|nes_plan_batch206:transport|nes_domain_reset124:hrelease|release_reset*}]
set f [open bus571.tsv w]
puts $f "corner\tport_group\tfrom\tto\tdata_delay"
proc emit571 {f c key group pin} {
 foreach_in_collection p [get_timing_paths -setup -from $group -to $pin -npaths 1] {
  puts $f [join [list $c $key [get_node_info -name [get_path_info -from $p]] [get_node_info -name [get_path_info -to $p]] [get_path_info -data_delay $p]] "\t"]
 }
}
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach group {SNES_READ_IN SNES_WRITE_IN {SNES_ADDR_IN[*]} SNES_ROMSEL_IN} {
  set port [get_ports $group]
  foreach_in_collection pin $outputs {emit571 $f $c $group $port $pin}
 }
 if {[string match *85c $c] && [get_collection_size $old]} {
  set oe [get_ports SNES_DATABUS_OE]
  if {[get_collection_size [get_timing_paths -from $old -to $oe -setup -npaths 1]]} {
   report_timing -setup -from $old -to $oe -npaths 1 -detail full_path -file bus571-oe.rpt
  }
 }
}
close $f
delete_timing_netlist
project_close
