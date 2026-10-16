# SPDX-License-Identifier: MIT
# Same fitted DB, full paths for actual related-clock failure and new source boundary.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal204.sdc
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 report_timing -setup -from [get_registers {*|control|check_next*}] -to [get_registers {*|reader|check_response_address*}] -npaths 10 -detail full_path -file paths204-$i-check.rpt
 report_timing -setup -from [get_registers {*|loader|release_reset*}] -to [get_registers {*|native_export|pack_count*}] -npaths 10 -detail full_path -file paths204-$i-epoch-status.rpt
 incr i
}
delete_timing_netlist
project_close
