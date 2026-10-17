# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal204.sdc
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 report_timing -setup -from [get_registers {*|boot|check_failed}] -to [get_registers {*|loader|byte_hold* *|loader|lane *|loader|chip *|loader|load_address*}] -npaths 4 -detail full_path -file payload218-$i-capture.rpt
 report_timing -setup -from [get_registers {*|loader_boot|*}] -to [get_registers {*|loader_boot|*}] -npaths 6 -detail full_path -file payload218-$i-boot.rpt
 incr i
}
delete_timing_netlist
project_close
