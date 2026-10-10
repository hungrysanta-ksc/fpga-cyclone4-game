# SPDX-License-Identifier: MIT
"""Selected placement boundaries; conditional IO envelope, not MTBF/signoff."""
from pathlib import Path
import argparse,csv,json,subprocess
TCL=r'''package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set f [open same-clock150.tsv w]
puts $f "corner\tclock\tkind\tfrom\tto\tslack"
set g [open io150.tsv w]
puts $g "corner\tgroup\tfrom\tto\tdelay\tslack"
set_max_delay 1000 -from [get_ports {ROM_DATA* SPI_* SNES_ADDR_IN* SNES_READ_IN SNES_WRITE_IN SNES_ROMSEL_IN SNES_DATA*}] -to [all_registers]
set_max_delay 1000 -from [all_registers] -to [get_ports {ROM_* SPI_MISO MCU_RDY SNES_DATA* SNES_DATABUS*}]
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach_in_collection clock [get_clocks *] {
  foreach kind {setup hold} {
   foreach_in_collection path [get_timing_paths -$kind -from_clock $clock -to_clock $clock -npaths 5] {
    puts $f "$corner\t[get_clock_info -name $clock]\t$kind\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"
   }
  }
 }
 foreach group {input output bundled recovery} {
  if {$group eq "input"} {
   set paths [get_timing_paths -setup -from [get_ports {ROM_DATA* SPI_* SNES_ADDR_IN* SNES_READ_IN SNES_WRITE_IN SNES_ROMSEL_IN SNES_DATA*}] -to [all_registers] -npaths 100000 -nworst 1000]
  } elseif {$group eq "output"} {
   set paths [get_timing_paths -setup -from [all_registers] -to [get_ports {ROM_* SPI_MISO MCU_RDY SNES_DATA* SNES_DATABUS*}] -npaths 100000 -nworst 1000]
  } elseif {$group eq "bundled"} {
   set paths [get_timing_paths -setup -from [get_registers {*pad*held_buttons*}] -to [get_registers {*pad*current_buttons*}] -npaths 100]
  } else {
   set paths [get_timing_paths -recovery -to [get_registers {*framebuffer* *consumer* *pad*}] -npaths 100000 -nworst 1000]
  }
  if {[get_collection_size $paths]==0 || [get_collection_size $paths]>=100000} {error "Empty or truncated inventory $group"}
  foreach_in_collection path $paths {
   puts $g "$corner\t$group\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -data_delay $path]\t[get_path_info -slack $path]"
  }
 }
}
close $f
close $g
delete_timing_netlist
project_close
'''
def main():
    p=argparse.ArgumentParser()
    for n in ['fit','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--reuse-tables',action='store_true')
    a=p.parse_args();o=a.fit
    assert not (o/'timing150-phase.json').exists()
    if a.reuse_tables:assert (o/'timing150.tcl').read_text()==TCL
    else:
      (o/'timing150.tcl').write_text(TCL,encoding='utf8',newline='\n')
      with (o/'timing150.log').open('wb') as f:
        r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t','timing150.tcl'],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=300)
      assert r.returncode==0,'timing150.log'
    rows=list(csv.DictReader((o/'same-clock150.tsv').open(),delimiter='\t'))
    setup=min(float(v['slack']) for v in rows if v['kind']=='setup')
    hold=min(float(v['slack']) for v in rows if v['kind']=='hold')
    io=list(csv.DictReader((o/'io150.tsv').open(),delimiter='\t'))
    din=max(float(v['delay']) for v in io if v['from'].startswith('ROM_DATA['))
    dout=max(float(v['delay']) for v in io if ':reader|' in v['from'] and v['to'].startswith(('ROM_ADDR[','ROM_1CE','ROM_2CE','ROM_OE')))
    sin=max(float(v['delay']) for v in io if v['group']=='input' and v['from'].startswith('SNES_'))
    sout=max(float(v['delay']) for v in io if v['group']=='output' and v['to'].startswith('SNES_'))
    #14 host cycles cover synchronizers, request/response and added address stage.
    envelope=14*11.904+sin+sout+6
    old_margin=16*5.952-70-din-dout-4
    # Address/chip launch at IDLE->SETUP, CE/OE at SETUP->ACTIVE.
    # Capture occurs16 edges after CE/OE,17 after address. Reset/owner signals
    # are stable throughout RUN; they are not per-read launch signals.
    reader=(o/'nes_rom_physical.sv').read_text()
    assert '.READ_CYCLES(16)' in (o/'nes_rom_boot.sv').read_text()
    assert 'SETUP:state<=ACTIVE;' in reader and 'if(state==SETUP)reading_active<=1;' in reader
    active=max(float(v['delay']) for v in io if ':reader|reading_active' in v['from'] and v['to'].startswith(('ROM_1CE','ROM_2CE','ROM_OE')))
    addr=max(float(v['delay']) for v in io if ':reader|' in v['from'] and v['to'].startswith('ROM_ADDR['))
    chip=max(float(v['delay']) for v in io if ':reader|chip' in v['from'] and v['to'].startswith(('ROM_1CE','ROM_2CE')))
    address_margin=17*5.952-70-max(addr,chip)-din-4
    active_margin=16*5.952-70-active-din-4
    margin=min(address_margin,active_margin)
    bundled=max(float(v['delay']) for v in io if v['group']=='bundled')
    negative=[v for v in io if v['group']=='recovery' and float(v['slack'])<0]
    # Only local release-chain async inputs may have raw async recovery slack.
    local_ok=all('host_release[' in v['to'] for v in negative)
    result=dict(passed=setup>=0 and hold>=0 and envelope<270 and margin>0 and bundled<40 and local_ok,
      same_clock_setup_ns=setup,same_clock_hold_ns=hold,snes_envelope_ns=envelope,sample_ns=270,
      psram_conditional_margin_ns=margin,pad_held_delay_ns=bundled,negative_recovery=negative,
      psram_address_margin_ns=address_margin,psram_active_margin_ns=active_margin,
      prior_unphased_margin_ns=old_margin,address_launch_cycles=17,ce_oe_launch_cycles=16,
      row_counts=[len(rows),len(io)],pcb_allowance_ns=2,mtbf_calculated=False,full_io_signoff=False,
      scope='Conditional routed boundaries; existing unmeasured electrical and clock-halt limits remain open.')
    (o/'timing150-phase.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='negative_recovery'}),flush=True)
    assert result['passed'],result
if __name__=='__main__':main()
