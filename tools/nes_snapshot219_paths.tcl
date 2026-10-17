# SPDX-License-Identifier: MIT
# Capture the residual status snapshot cone; do not alter constraints.
package require ::quartus::sta
project_open board
foreach view {implementation nominal} {
 create_timing_netlist
 if {$view eq "nominal"} {read_sdc nominal204.sdc} else {read_sdc}
 set i 0
 foreach corner [get_available_operating_conditions] {
  set_operating_conditions $corner
  update_timing_netlist
  report_timing -setup -to [get_registers {*|control|snapshot*}] -npaths 8 -detail full_path -file snapshot219-$view-$i-status.rpt
  report_timing -setup -from [get_registers {*|control|load_valid}] -to [get_registers {*|loader|phase*}] -npaths 4 -detail full_path -file snapshot219-$view-$i-receive.rpt
  incr i
 }
 delete_timing_netlist
}
project_close
