# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal204.sdc
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 report_timing -setup -from [get_registers {*|content_lifetime|serial*}] -to [get_registers {*|content_lifetime|gray*}] -npaths 4 -detail full_path -file epoch217-$i-gray.rpt
 incr i
}
delete_timing_netlist
project_close
