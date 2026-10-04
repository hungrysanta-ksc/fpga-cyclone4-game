project_open pin
create_timing_netlist
read_sdc
foreach op [get_available_operating_conditions] {
 set_operating_conditions $op
 update_timing_netlist
 report_metastability -nchains 100 -file "cdc-metastability-$op.rpt"
}
project_close
