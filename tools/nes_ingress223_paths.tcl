# SPDX-License-Identifier: MIT
# Read-only exact residual and changed exporter paths; no timing exceptions.
package require ::quartus::sta
project_open board
foreach view {implementation nominal} {
 create_timing_netlist
 if {$view eq "nominal"} {read_sdc nominal204.sdc} else {read_sdc}
 set i 0
 foreach corner [get_available_operating_conditions] {
  set_operating_conditions $corner
  update_timing_netlist
  report_timing -setup -from [get_registers {*|reader|check_response_address*}] -to [get_registers {*|control|commit_clear}] -npaths 4 -detail full_path -file ingress223-$view-$i-counter.rpt
  report_timing -setup -to [get_registers {*|native_export|*}] -npaths 4 -detail full_path -file ingress223-$view-$i-export.rpt
  incr i
 }
 delete_timing_netlist
}
project_close
