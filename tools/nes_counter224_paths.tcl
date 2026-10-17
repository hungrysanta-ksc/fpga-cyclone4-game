# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
foreach view {implementation nominal} {
 create_timing_netlist
 if {$view eq "nominal"} {read_sdc nominal204.sdc} else {read_sdc}
 set i 0
 foreach corner [get_available_operating_conditions] {
  set_operating_conditions $corner
  update_timing_netlist
  report_timing -setup -from [get_registers {*|control|command*}] -to [get_registers {*|control|raw_*}] -npaths 4 -detail full_path -file counter224-$view-$i-sample.rpt
  report_timing -setup -to [get_registers {*|control|commit_*}] -npaths 4 -detail full_path -file counter224-$view-$i-counter.rpt
  incr i
 }
 delete_timing_netlist
}
project_close
