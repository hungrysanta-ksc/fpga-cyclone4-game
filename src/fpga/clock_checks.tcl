project_open pin
create_timing_netlist
read_sdc
foreach op [get_available_operating_conditions] {
 set_operating_conditions $op
 update_timing_netlist
 check_timing -file "check-$op.rpt"
 report_min_pulse_width -nworst 20 -file "pulse-$op.rpt"
}
report_clocks -file full-clocks.rpt
report_clock_transfers -file full-clock-transfers.rpt
report_ucp -file full-unconstrained.rpt
project_close
