project_open pin
create_timing_netlist
read_sdc
foreach op [get_available_operating_conditions] {
 set_operating_conditions $op
 update_timing_netlist
 report_net_delay -file "cdc-net-$op.rpt"
 report_timing -setup -from [get_registers {*writer|entries* *uploader|held_*}] -to [get_registers {*host_frontend|writer|data_next* *host_frontend|writer|held_high* *host_frontend|writer|held_word *host_frontend|writer|addr_next* *host_frontend|writer|slot_violation *uploader|bus_page *uploader|bus_front_valid}] -npaths 100 -detail full_path -file "cdc-bundle-$op.rpt"
 report_timing -recovery -npaths 20 -detail full_path -file "recovery-$op.rpt"
 report_timing -removal -npaths 20 -detail full_path -file "removal-$op.rpt"
}
project_close
