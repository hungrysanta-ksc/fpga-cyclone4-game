project_open pin
create_timing_netlist
read_sdc
foreach op [get_available_operating_conditions] {
 set_operating_conditions $op
 update_timing_netlist
 foreach {group source target} {
  addr {*host_frontend|writer|ram_addr*} {RAM_ADDR[*]}
  data {*host_frontend|writer|pad_data*} {RAM_DATA[*]}
  drive {*host_frontend|writer|drive_reg*} {RAM_DATA[*]}
  we {*host_frontend|writer|we_reg} {RAM_WE}
  oe {*host_frontend|writer|oe_reg} {RAM_OE}
 } {
  foreach kind {setup hold} {
   report_timing -$kind -from [get_registers $source] -to [get_ports $target] -npaths 200 -nworst 20 -detail full_path -file "sram-pad-$group-$kind-$op.rpt"
  }
 }
}
project_close
