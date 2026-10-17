# SPDX-License-Identifier: MIT
# Exact residual paths in both production and nominal clock views.
package require ::quartus::sta
project_open board
foreach view {implementation nominal} {
 create_timing_netlist
 if {$view eq "nominal"} {read_sdc nominal204.sdc} else {read_sdc}
 set i 0
 foreach corner [get_available_operating_conditions] {
  set_operating_conditions $corner
  update_timing_netlist
  report_timing -setup -from [get_registers {*|control|fault}] -to [get_registers {*|boot|check_failed}] -npaths 2 -detail full_path -file fault219-$view-$i-owner.rpt
  report_timing -setup -from [get_registers {*|control|command*}] -to [get_registers {*|control|raw_causes*}] -npaths 3 -detail full_path -file fault219-$view-$i-command.rpt
  report_timing -setup -from [get_registers {*|reader|check_response_address*}] -to [get_registers {*|control|fault *|control|error_code* *|control|load_end *|control|commit_inc *|control|commit_clear}] -npaths 6 -detail full_path -file fault219-$view-$i-response.rpt
  incr i
 }
 delete_timing_netlist
}
project_close
