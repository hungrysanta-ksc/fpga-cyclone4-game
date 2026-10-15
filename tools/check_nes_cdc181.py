# SPDX-License-Identifier: MIT
"""Fail closed on CDC exception scope, endpoint loss and physical data budget.

Generate a Standard STA script, then verify its raw TSVs. Post-map mode checks
coverage only. Routed mode also requires all-corner path/chain budgets; it is
not complete board IO, whole-design timing, metastability or hardware approval.
"""
from pathlib import Path
import argparse,csv,json
from nes_game147 import sha
from nes_cdc181 import EXACT

def generate(folder,post_map):
    m=json.loads((folder/'preparation.json').read_bytes())
    for n,h in m['sources'].items():assert sha(folder/n)==h,n
    f=folder/'check-cdc181.tcl';assert not f.exists()
    script='package require ::quartus::sta\nproject_open board\ncreate_timing_netlist'+(' -post_map' if post_map else '')+'\nread_sdc\n'+EXACT
    script+='set selected181 {\n'
    for x in m['selected']:
        script+=' {'+' '.join('{'+v+'}' for v in (x['group'],x['source'],x['destination'],x.get('second_stage','')))+'}\n'
    script+='}\n'
    script+='''set f [open cdc181-paths.tsv w]
puts $f "corner\tgroup\tkind\tfrom\tto\tdelay\tslack\trelationship"
set top [open cdc181-topology.tsv w]
puts $top "first\tsecond"
foreach row $selected181 {
 lassign $row group src dst second
 if {$group ne "first_stage"} {continue}
 set fs [get_fanouts [cdc181_exact $dst]]
 if {[get_collection_size $fs]!=1} {error "CDC181 first-stage fanout: $dst"}
 foreach_in_collection v $fs {
  set n [get_node_info -name $v]
  if {$n ne $second} {error "CDC181 stage mismatch: $dst -> $n"}
  puts $top "$dst\t$n"
 }
}
close $top
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach row $selected181 {
  lassign $row group src dst second
  foreach kind {setup hold} {
   set ps [get_timing_paths -$kind -from [cdc181_exact $src] -to [cdc181_exact $dst] -npaths 1]
   set expected [expr {$group ne "first_stage" && $kind eq "setup"}]
   if {[get_collection_size $ps]!=$expected} {error "CDC181 exception coverage: $group $kind $src -> $dst"}
   foreach_in_collection p $ps {
    puts $f "$corner\t$group\t$kind\t$src\t$dst\t[get_path_info -data_delay $p]\t[get_path_info -slack $p]\t[get_path_info -clock_relationship $p]"
   }
   if {$group ne "first_stage"} {continue}
   set ps [get_timing_paths -$kind -from [cdc181_exact $dst] -to [cdc181_exact $second] -npaths 1]
   if {[get_collection_size $ps]!=1} {error "CDC181 downstream timing lost: $dst"}
   foreach_in_collection p $ps {
    if {[get_path_info -from_clock $p]!=[get_path_info -to_clock $p]} {error "CDC181 chain crosses clocks"}
    puts $f "$corner\tchain\t$kind\t$dst\t$second\t[get_path_info -data_delay $p]\t[get_path_info -slack $p]\t[get_path_info -clock_relationship $p]"
   }
  }
 }
}
close $f
report_exceptions -setup -npaths 100000 -pairs_only -file cdc181-setup-exceptions.rpt
report_exceptions -hold -npaths 100000 -pairs_only -file cdc181-hold-exceptions.rpt
delete_timing_netlist
project_close
'''
    f.write_text(script,encoding='utf8')
    print('Generated',f,'post_map=',post_map)

def verify(folder,post_map,original,out):
    assert not out.exists()
    m=json.loads((folder/'preparation.json').read_bytes())
    for n,h in m['sources'].items():assert sha(folder/n)==h,n
    assert int((folder/'check-cdc181.exitcode').read_text(encoding='utf-8-sig'))==0
    rows=lambda p:list(csv.DictReader(p.open(),delimiter='\t'))
    xs=rows(folder/'cdc181-paths.tsv');top=rows(folder/'cdc181-topology.tsv')
    assert len(top)==17 and len(xs)==3*(128+34),(len(top),len(xs))
    lookup={(x['source'],x['destination']):x for x in m['selected']}
    for x in xs:
        if x['group']=='chain':continue
        spec=lookup[(x['from'],x['to'])]
        assert abs(float(x['relationship'])-spec['setup_bound_ns'])<0.002,x
    physical_pass=all(float(x['delay'])<lookup[(x['from'],x['to'])]['data_delay_budget_ns'] for x in xs if x['group']!='chain')
    slack_pass=all(float(x['slack'])>=0 for x in xs)
    if not post_map:assert physical_pass and slack_pass,'routed CDC budget violation'
    scope=None
    if original:
        # Same mapped RTL: every unmodified crossing/reset pair must remain timed.
        before=rows(original/'inventory181.tsv');after=rows(folder/'inventory181.tsv')
        key=lambda x:(x['kind'],x['from_clock'],x['to_clock'],x['from'],x['to'])
        b={key(x) for x in before};a={key(x) for x in after}
        removed=b-a;extra=a-b;expected=set()
        for x in before:
            spec=lookup.get((x['from'],x['to']))
            if spec and (x['kind'] in ('setup','hold') if spec['group']=='first_stage' else x['kind']=='hold'):
                expected.add(key(x))
        assert removed==expected and not extra,(len(removed),len(expected),len(extra))
        assert not any(x[0] in ('recovery','removal') for x in removed)
        scope=dict(before_pairs=len(b),after_pairs=len(a),removed_pairs=len(removed),unexpected_removed=0,
                   recovery_removal_unchanged=True,same_pll_pairs_unchanged=True)
    result=dict(passed=True,post_map=post_map,routed_approval=not post_map,
                selected_pairs=len(m['selected']),payload_pairs=128,first_stages=17,raw_rows=len(xs),
                physical_budget_pass=physical_pass,constrained_slack_pass=slack_pass,scope=scope,
                min_slack_ns=min(float(x['slack']) for x in xs),
                groups={g:dict(max_data_delay_ns=max(float(x['delay']) for x in xs if x['group']==g),
                               min_slack_ns=min(float(x['slack']) for x in xs if x['group']==g))
                        for g in sorted({x['group'] for x in xs})},
                files={n:sha(folder/n) for n in ['preparation.json','check-cdc181.tcl','cdc181-paths.tsv','cdc181-topology.tsv','check-cdc181.log']},
                hardware=False,whole_design_timing_approval=False)
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['generate','verify'])
    p.add_argument('--folder',type=Path,required=True);p.add_argument('--post-map',action='store_true')
    p.add_argument('--original',type=Path);p.add_argument('--out',type=Path)
    a=p.parse_args()
    if a.action=='generate':generate(a.folder,a.post_map)
    else:verify(a.folder,a.post_map,a.original,a.out)
