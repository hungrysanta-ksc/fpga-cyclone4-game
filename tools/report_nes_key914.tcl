# Run in the fitted 914F project. Report each bundled data bit separately.
project_open board
create_timing_netlist -model slow
read_sdc
update_timing_netlist
set path {nes_live_joint:core|nes_direct206:direct_path|nes_plan_batch206:transport}
for {set bit 0} {$bit < 11} {incr bit} {
    set src [cdc181_exact [format {%s|nes_native_mailbox206:control|held[%d]} $path [expr {$bit+5}]]]
    set dst [cdc181_exact [format {%s|spec_key[%d]} $path $bit]]
    set p [get_timing_paths -setup -from $src -to $dst -npaths 1]
    if {[get_collection_size $p] != 1} {error "missing mailbox path for bit $bit"}
    foreach_in_collection match $p {
        set margin [get_path_info -slack $match]
        puts "KEY914 bit=$bit slack=$margin"
        if {$margin < 0} {error "mailbox setup failed for bit $bit"}
    }
}
delete_timing_netlist
project_close
