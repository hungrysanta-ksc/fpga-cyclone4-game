# SPDX-License-Identifier: MIT
"""Inventory existing negative endpoints; do not generate timing exceptions."""
import argparse,csv,json,re
from pathlib import Path
from nes_raw506 import sha

def rows(path):
    with path.open() as f:return list(csv.DictReader(f,delimiter='\t'))

def classify(r):
    s,d=r['from'],r['to']
    leaf=d.split('|')[-1]
    if r['check']=='setup':
        if r['from_clock']==r['to_clock']:return 'synchronous_data'
        if 'content_lifetime|epoch_meta[' in d:return 'gray_first'
        if leaf.endswith('[0]') and re.match(r'(ref_ok_mem|h_to_n|n_to_h|errors_h|up_dst|up_src|ack_sync|req_sync|active_sync)\[0\]$',leaf):return 'single_bit_first'
        if '|held[' in s and ('|received[' in d or '|nes_plan_batch206:transport|' in d):return 'held_mailbox'
        if '|nes_rom_physical:reader|address_hold[' in s:return 'held_rom_address'
        if 'nes_screen_status151:screen_status|snapshot[' in d:return 'raw_diagnostic_pin'
        if (':core_release|release_reset[' in s and any(v in d for v in ('nes_native_spi165:native_spi','nes_native_mailbox165:native_records','nes_native_mailbox165:native_prepared'))) or ('|nes_rom_physical:reader|' in d and any(v in s for v in ('|check_failed','|nes_rom_loader:loader|phase['))):return 'legacy_raw_control'
    if r['check']=='recovery':
        if re.search(r'\|(release_reset|release_pipe|source_reset|memory_reset|dac_release|sr|dr)\[[01]\]$',d):return 'reset_release_chain'
        if re.search(r'(^|\|)(idle_ss|idle_write|sink_rom_fault)\[[01]\]$',d):return 'raw_reset_input_sampler'
        if d.endswith('|host_ready'):return 'raw_reset_guarded_state'
    raise AssertionError(('unclassified endpoint',r))

def prepare(board,out):
    out.mkdir(parents=True,exist_ok=False)
    raw=rows(board/'boundary575-negative.tsv')
    for r in raw:r['class']=classify(r)
    (out/'classified.json').write_text(json.dumps(raw,indent=2)+'\n',newline='\n')
    chains={}
    for r in raw:
        d=r['to'];k=r['class']
        if k=='gray_first':first=d;second=d.replace('|epoch_meta[','|epoch_sync[')
        elif k=='single_bit_first':first=d;second=d[:-3]+'[1]'
        elif k=='reset_release_chain':first=d[:-3]+'[0]';second=d[:-3]+'[1]'
        else:continue
        chains[first]=(k,second)
    script='''package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
proc exact {name} {
 set r [get_registers $name]
 if {[get_collection_size $r]!=1} {error "missing endpoint: $name"}
 return $r
}
set pairs {
'''
    for f,(kind,s) in sorted(chains.items()):script+=' {'+' '.join('{'+v+'}' for v in (kind,f,s))+'}\n'
    script+='''}
set out [open boundary575-topology.tsv w]
puts $out "class\tfirst\texpected_second\tfanout"
foreach row $pairs {
 lassign $row kind first second
 exact $second
 foreach_in_collection n [get_fanouts [exact $first]] {
  puts $out [join [list $kind $first $second [get_node_info -name $n]] "\t"]
 }
}
close $out
set out [open boundary575-chains.tsv w]
puts $out "corner\tclass\tcheck\tfirst\tsecond\tslack\tdelay"
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach row $pairs {
  lassign $row kind first second
  foreach check {setup hold} {
   set ps [get_timing_paths -$check -from [exact $first] -to [exact $second] -npaths 1]
   if {[get_collection_size $ps]!=1} {error "missing settling path $first -> $second"}
   foreach_in_collection p $ps {
    if {[get_path_info -from_clock $p]!=[get_path_info -to_clock $p]} {error "cross-clock settling path"}
    puts $out [join [list $c $kind $check $first $second [get_path_info -slack $p] [get_path_info -data_delay $p]] "\t"]
   }
  }
 }
}
close $out
delete_timing_netlist
project_close
'''
    (out/'chains575.tcl').write_text(script,newline='\n')
    # Measurement in a temporary timing netlist, never a board SDC change.
    # An immutable mailbox is sampled >=3 destination edges after publication;
    # ROM address capture is >=2 periods later. Use 2 destination periods as
    # a conservative data budget, and leave raw reset/control timing untouched.
    pairs={}
    for r in raw:
        if r['class'] in ('held_mailbox','held_rom_address'):
            pairs[(r['from'],r['to'])]=(r['class'],r['to_clock'])
    script='''package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
proc exact {name} {
 set r [get_registers $name]
 if {[get_collection_size $r]!=1} {error "missing endpoint $name"}
 return $r
}
set pairs {
'''
    for (src,dst),(kind,clock) in sorted(pairs.items()):
        script+=' {'+' '.join('{'+v+'}' for v in (kind,src,dst,clock))+'}\n'
    script+='''}
foreach row $pairs {
 lassign $row kind src dst clock
 set budget [expr {2.0*[get_clock_info -period [get_clocks $clock]]}]
 set_max_delay $budget -from [exact $src] -to [exact $dst]
}
set out [open boundary575-held-budget.tsv w]
puts $out "corner\tclass\tfrom\tto\tbudget\tslack\tdelay"
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach row $pairs {
  lassign $row kind src dst clock
  set budget [expr {2.0*[get_clock_info -period [get_clocks $clock]]}]
  set ps [get_timing_paths -setup -from [exact $src] -to [exact $dst] -npaths 1]
  if {[get_collection_size $ps]!=1} {error "missing held-data path"}
  foreach_in_collection p $ps {
   puts $out [join [list $c $kind $src $dst $budget [get_path_info -slack $p] [get_path_info -data_delay $p]] "\t"]
  }
 }
}
close $out
delete_timing_netlist
project_close
'''
    (out/'held575.tcl').write_text(script,newline='\n')
    (out/'inputs.json').write_text(json.dumps({p.name:sha(p) for p in [board/'boundary575-negative.tsv',board/'board.sdc',board/'cdc181.sdc',board/'output_files/board.sof']},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--board',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();prepare(a.board,a.out)
