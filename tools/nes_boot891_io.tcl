# Inspect fitted pad fanout without adding timing exceptions or delays.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
update_timing_netlist
set f [open boot891-inputs.tsv w]
foreach_in_collection pin [get_ports *] {
    if {![get_port_info -is_input_port $pin] && ![get_port_info -is_inout_port $pin]} {continue}
    set ports [get_ports [get_node_info -name $pin]]
    if {[get_collection_size $ports] != 1} {error "missing port"}
    foreach_in_collection endpoint [get_fanouts $ports] {
        puts $f "[get_node_info -name $pin]\t[get_node_info -name $endpoint]"
    }
}
close $f
delete_timing_netlist
project_close
