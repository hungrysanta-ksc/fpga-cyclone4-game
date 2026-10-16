# SPDX-License-Identifier: MIT
# Same205 fitted DB: remaining completion predicate path, no placement changes.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal204.sdc
set i 0
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 report_timing -setup -from [get_registers {*|loader|loaded_bytes*}] -to [get_registers {*|loader|count_complete}] -npaths 10 -detail full_path -file paths205-$i-complete.rpt
 report_timing -setup -from [get_registers {*|loader|release_reset*}] -to [get_registers {*|native_export|pack_count*}] -npaths 10 -detail full_path -file paths204-$i-epoch-status.rpt
 incr i
}
delete_timing_netlist
project_close
