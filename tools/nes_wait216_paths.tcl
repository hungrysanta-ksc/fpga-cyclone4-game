# SPDX-License-Identifier: MIT
# Read-only paths on216 fitted DB; no constraint or placement change.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal204.sdc
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 report_timing -setup -from [get_registers {*|control|load_valid}] -to [get_registers {*|loader|error_code*}] -npaths 4 -detail full_path -file wait216-$i-loader.rpt
 report_timing -setup -from [get_registers {*|tile|cycles*}] -npaths 4 -detail full_path -file wait216-$i-counter.rpt
 incr i
}
delete_timing_netlist
project_close
