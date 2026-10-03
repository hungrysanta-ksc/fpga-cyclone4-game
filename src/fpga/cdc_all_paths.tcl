project_open pin
create_timing_netlist
read_sdc
foreach op [get_available_operating_conditions] {
 set_operating_conditions $op
 update_timing_netlist
 report_timing -setup -npaths 20 -detail full_path -file "all-setup-$op.rpt"
 report_timing -hold -npaths 20 -detail full_path -file "all-hold-$op.rpt"
}
project_close
