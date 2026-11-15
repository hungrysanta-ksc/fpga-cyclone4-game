package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set f [open paths801.tsv w]
puts $f "corner\tcheck\tslack_ns\tfrom\tto"
foreach c [get_available_operating_conditions] {
    set_operating_conditions $c
    update_timing_netlist
    set pairs {
        {nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|check_failed}
        {nes_screen_status151:screen_status|drive_sync[0]}
        {nes_live_joint:core|nes_domain_reset124:diagnostic_release|release_reset[1]}
        {nes_sink_bridge165:sink|nes_sink_spi165:endpoint|snapshot[131]}
    }
    set new_stop {nes_sink_bridge165:sink|nes_sink_spi165:endpoint|stop_at_command}
    if {[get_collection_size [get_registers -nowarn $new_stop]] == 1} {
        set pairs [lreplace $pairs 3 3 $new_stop]
    }
    foreach {src dst} $pairs {
        foreach check {setup hold} {
            set paths [get_timing_paths -$check -from [cdc181_exact $src] -to [cdc181_exact $dst] -npaths 1]
            if {[get_collection_size $paths] != 1} {error "Missing $check path $src -> $dst"}
            foreach_in_collection p $paths {
                puts $f [join [list $c $check [get_path_info -slack $p] $src $dst] "\t"]
            }
        }
    }
}
close $f
delete_timing_netlist
project_close
