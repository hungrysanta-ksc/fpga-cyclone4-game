project_open pin
create_timing_netlist
read_sdc
set_output_delay -clock sys -max 0 [get_ports {ROM_WE ROM_DATA[*]}]
set_output_delay -clock sys -min 0 [get_ports {ROM_WE ROM_DATA[*]}]
foreach board {0 3 5} {
 set_input_delay -clock sys -max [expr {82.6+$board}] [get_ports {ROM_DATA[*]}]
 foreach op [get_available_operating_conditions] {
 set_operating_conditions $op
 update_timing_netlist
 report_timing -setup -from [get_registers *] -to [get_ports {ROM_WE ROM_DATA[*] ROM_ADDR[*] ROM_1CE ROM_2CE ROM_OE ROM_BHE ROM_BLE}] -npaths 100 -detail full_path -file "write-max-board$board-$op.rpt"
 report_timing -hold -from [get_registers *] -to [get_ports {ROM_WE ROM_DATA[*] ROM_ADDR[*] ROM_1CE ROM_2CE ROM_OE ROM_BHE ROM_BLE}] -npaths 100 -detail full_path -file "write-min-board$board-$op.rpt"
 report_timing -setup -from [get_registers *] -to [get_registers *] -npaths 10 -detail full_path -file "internal-board$board-$op.rpt"
 report_timing -hold -from [get_registers *] -to [get_registers *] -npaths 10 -detail full_path -file "internal-hold-board$board-$op.rpt"
 report_timing -setup -from [get_registers {*rsp_data*}] -to [get_registers {*core*}] -npaths 5 -detail full_path -file "forward-board$board-$op.rpt"
 report_timing -setup -to [get_ports {ROM_ADDR[*] ROM_1CE ROM_2CE ROM_OE ROM_BHE ROM_BLE}] -npaths 26 -detail full_path -file "out-board$board-$op.rpt"
 report_timing -setup -from [get_ports {ROM_DATA[*]}] -npaths 16 -detail full_path -file "in-board$board-$op.rpt"
 report_timing -hold -from [get_ports {ROM_DATA[*]}] -npaths 16 -detail full_path -file "hold-board$board-$op.rpt"
 }
}
report_clocks -file clocks.rpt
project_close
