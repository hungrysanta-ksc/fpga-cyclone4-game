# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal181.sdc
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 set src [get_registers {*reader*check_response_address* *reader*chip *reader*check_request_tag*}]
 set dst [get_registers {*control|verified *control|check_enable}]
 if {[get_collection_size $src]==0 || [get_collection_size $dst]==0} {error "Missing CHECK endpoints"}
 report_timing -setup -from $src -to $dst -npaths 20 -detail full_path -file oamports181-$corner-check.rpt
}
delete_timing_netlist
project_close
