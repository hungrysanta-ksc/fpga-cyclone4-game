# SPDX-License-Identifier: MIT
# Exact same-mem-clock failure inventory, without broad asynchronous paths.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal204.sdc
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 report_timing -setup -from [get_registers {*|reader|check_response_address*}] -to [get_registers {*|control|load_end *|control|load_begin *|control|load_valid *|control|start *|control|stop}] -npaths 6 -detail full_path -file finish218-$i-response.rpt
 report_timing -setup -from [get_registers {*|loader|phase*}] -to [get_registers {*|loader|loaded_bytes*}] -npaths 4 -detail full_path -file finish218-$i-count.rpt
 incr i
}
delete_timing_netlist
project_close
