# SPDX-License-Identifier: MIT
"""Exact CDC extension to the original cdc181 constraints; no clock-group waiver."""
import argparse,json,re
from pathlib import Path
from nes_boundary575 import rows,classify as classify575
from nes_raw506 import sha

def period(clock):
    if clock=='nes':return 45.454
    if clock.endswith('pll1|clk[0]'):return 11.904
    if clock.endswith('pll1|clk[1]'):return 5.952
    raise AssertionError(('unreviewed clock',clock))

def classify(r):
    q=dict(r)
    q['check']={'hold':'setup','removal':'recovery'}.get(r['check'],r['check'])
    if q['check']=='setup' and q['to']=='nes_screen_status151:screen_status|drive_sync[0]':return 'single_bit_first'
    if q['check']=='recovery' and re.fullmatch(r'nes_game_pad150:pad\|host_release\[[01]\]',q['to']):return 'reset_release_chain'
    return classify575(q)

def generate(board,out,diagnostic=False):
    out.mkdir(parents=True,exist_ok=False)
    s=(board/'cdc181.sdc').read_text()
    old={(a,b):float(v) for v,a,b in re.findall(r'set_max_delay ([\d.]+) -from \[cdc181_exact \{([^}]+)\}\] -to \[cdc181_exact \{([^}]+)\}\]',s)}
    pairs={}
    for r in rows(board/'cdc576-all.tsv'):
        try:k=classify(r)
        except AssertionError:continue # Remain covered by cdc181, or remain raw.
        if k not in ('single_bit_first','gray_first','held_mailbox','held_rom_address'):continue
        src,dst=r['from'],r['to']
        target_period=period(r['to_clock'])
        first=k in ('single_bit_first','gray_first')
        budget=target_period if first else 2*target_period
        if k=='gray_first':
            source_period=period(r['from_clock'])
            budget=min(budget,source_period)
        budget=min(budget,old.get((src,dst),budget)) # Never relax a prior data bound.
        second=(dst.replace('|epoch_meta[','|epoch_sync[') if k=='gray_first' else dst[:-3]+'[1]') if first else ''
        if k=='gray_first':assert src==dst.replace('|epoch_meta[','|gray[')
        pairs[src,dst]=dict(kind=k,source=src,destination=dst,second=second,budget_ns=budget)
    if diagnostic:assert any(r['destination'].endswith('|drive_sync[0]') for r in pairs.values())
    # The 575 verified release chains: exceptions terminate only at CLRN,
    # never at D/ASDATA or the reset output's synchronous consumers.
    negative=board/'raw576-negative.tsv'
    if not negative.exists():negative=board/'boundary575-negative.tsv'
    resets=sorted({r['to'][:-3]+f'[{i}]' for r in rows(negative) if classify(r)=='reset_release_chain' for i in (0,1)})
    pre='''# CDC576 exact extension. cdc181.sdc must already be loaded.
proc cdc576_pin {regname} {
 set pinname [regsub -all {[^|:]+:} $regname {}]
 append pinname "|clrn"
 set p [get_pins $pinname]
 if {[get_collection_size $p]!=1} {error "CDC576 missing reset pin $pinname"}
 return $p
}
'''
    lines=[pre]
    for row in pairs.values():
        a,b=row['source'],row['destination']
        lines.append(f"# {row['kind']}")
        lines.append(f"set_max_delay {row['budget_ns']:.3f} -from [cdc181_exact {{{a}}}] -to [cdc181_exact {{{b}}}]")
        lines.append(f"set_false_path -hold -from [cdc181_exact {{{a}}}] -to [cdc181_exact {{{b}}}]")
    for name in resets:
        lines.append(f'set_false_path -to [cdc576_pin {{{name}}}]')
    (out/'cdc576.sdc').write_text('\n'.join(lines)+'\n',newline='\n')
    chains={r['destination']:r['second'] for r in pairs.values() if r['second']}
    chains.update({n:n[:-3]+'[1]' for n in resets if n.endswith('[0]')})
    verify='''package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
source cdc576.sdc
set chains {
'''
    verify+='\n'.join(' {'+' '.join('{'+v+'}' for v in (a,b))+'}' for a,b in sorted(chains.items()))
    verify+='\n}\nset data {\n'
    verify+='\n'.join(' {'+' '.join('{'+str(v)+'}' for v in (r['kind'],r['source'],r['destination'],r['budget_ns']))+'}' for r in pairs.values())
    verify+='''
}
set f [open cdc576-settling.tsv w]
puts $f "corner\tcheck\tfirst\tsecond\tslack\tdelay"
set g [open cdc576-bounded.tsv w]
puts $g "corner\tkind\tfrom\tto\tbudget\tslack\tdelay"
foreach row $chains {
 lassign $row first second
 set next [get_fanouts [cdc181_exact $first]]
 if {[get_collection_size $next]!=1} {error "CDC576 extra first-stage fanout $first"}
 foreach_in_collection n $next {if {[get_node_info -name $n]!=$second} {error "CDC576 incorrect next stage $first"}}
}
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach row $chains {
  lassign $row first second
  foreach kind {setup hold} {
   set ps [get_timing_paths -$kind -from [cdc181_exact $first] -to [cdc181_exact $second] -npaths 1]
   if {[get_collection_size $ps]!=1} {error "CDC576 lost real settling check $first $kind"}
   foreach_in_collection p $ps {
    if {[get_path_info -from_clock $p]!=[get_path_info -to_clock $p]} {error "CDC576 cross-clock next stage"}
    set slack [get_path_info -slack $p]
    if {$slack<0} {error "CDC576 failed settling $first $kind $slack"}
    puts $f [join [list $c $kind $first $second $slack [get_path_info -data_delay $p]] "\t"]
   }
  }
 }
 foreach row $data {
  lassign $row kind src dst budget
  set ps [get_timing_paths -setup -from [cdc181_exact $src] -to [cdc181_exact $dst] -npaths 1]
  if {[get_collection_size $ps]!=1} {error "CDC576 lost finite data bound $src $dst"}
  foreach_in_collection p $ps {
   set slack [get_path_info -slack $p]
   if {$slack<0} {error "CDC576 failed data bound $src $dst $slack"}
   puts $g [join [list $c $kind $src $dst $budget $slack [get_path_info -data_delay $p]] "\t"]
  }
 }
}
close $f
close $g
delete_timing_netlist
project_close
'''
    (out/'verify576.tcl').write_text(verify,newline='\n')
    result=dict(pairs=list(pairs.values()),reset_registers=resets,
        input_inventory=sha(board/'cdc576-all.tsv'),original_SDC=sha(board/'cdc181.sdc'),
        original_SOF=sha(board/'output_files/board.sof'),constraints=sha(out/'cdc576.sdc'))
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--board',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--diagnostic',action='store_true');a=p.parse_args();generate(a.board,a.out,a.diagnostic)
