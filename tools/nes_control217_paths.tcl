# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal204.sdc
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 report_timing -setup -from [get_registers {*|control|bit_count*}] -to [get_registers {*|control|offset*}] -npaths 4 -detail full_path -file control217-$i-offset.rpt
 incr i
}
delete_timing_netlist
project_close
