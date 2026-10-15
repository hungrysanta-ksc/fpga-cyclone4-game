# SPDX-License-Identifier: MIT
"""Check eight captured bytes, exact timing scope and routed physical bound."""
from pathlib import Path
import argparse,csv,json
from nes_game147 import sha

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['generate','verify'])
    p.add_argument('--folder',type=Path,required=True);p.add_argument('--post-map',action='store_true')
    p.add_argument('--out',type=Path);a=p.parse_args();d=a.folder
    m=json.loads((d/'preparation.json').read_bytes())
    for n,h in m['sources'].items():assert sha(d/n)==h,n
    if a.action=='generate':
        s='package require ::quartus::sta\nproject_open board\ncreate_timing_netlist'+(' -post_map' if a.post_map else '')+'\nread_sdc\n'
        s+='set reply_pairs {\n'+''.join(' {{'+x['source']+'} {'+x['destination']+'}}\n' for x in m['reply_selected'])+'}\n'
        s+='''set f [open reply181-paths.tsv w]
puts $f "corner\tfrom\tto\tdelay\tslack\trelationship"
set fan [open reply181-cone.tsv w]
puts $fan "corner\tfrom\tto\tfrom_clock\tto_clock"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach pair $reply_pairs {
  lassign $pair src dst
  set source [cdc181_exact $src];set dest [cdc181_exact $dst]
  set paths [get_timing_paths -setup -from $source -to $dest -npaths 2]
  if {[get_collection_size $paths]!=1} {error "reply setup missing/duplicated $src"}
  if {[get_collection_size [get_timing_paths -hold -from $source -to $dest -npaths 2]]!=0} {error "reply hold exception missing"}
  foreach_in_collection path $paths {
   puts $f "$corner\t$src\t$dst\t[get_path_info -data_delay $path]\t[get_path_info -slack $path]\t[get_path_info -clock_relationship $path]"
  }
  set paths [get_timing_paths -setup -from $source -to_clock [get_clocks nes] -npaths 10000 -nworst 1000]
  if {[get_collection_size $paths]!=1} {error "held-data still fans into multiple NES endpoints $src"}
  foreach_in_collection path $paths {
   if {[get_node_info -name [get_path_info -to $path]] ne $dst} {error "unexpected NES consumer"}
   puts $fan "$corner\t$src\t$dst\t[get_clock_info -name [get_path_info -from_clock $path]]\t[get_clock_info -name [get_path_info -to_clock $path]]"
  }
  # All downstream data endpoints must now be in the NES clock domain.
  set paths [get_timing_paths -setup -from $dest -npaths 10000 -nworst 1000]
  if {[get_collection_size $paths]==0 || [get_collection_size $paths]>=10000} {error "reply downstream missing/truncated"}
  foreach_in_collection path $paths {
   if {[get_clock_info -name [get_path_info -from_clock $path]] ne "nes" || [get_clock_info -name [get_path_info -to_clock $path]] ne "nes"} {error "reply downstream crosses clock"}
  }
 }
}
close $f
close $fan
delete_timing_netlist
project_close
'''
        f=d/'check-reply181.tcl';assert not f.exists();f.write_text(s,encoding='utf8')
        print('Generated exact reply scope / eight capture / downstream clock audit')
    else:
        assert int((d/'check-reply181.exitcode').read_text(encoding='utf-8-sig'))==0
        xs=list(csv.DictReader((d/'reply181-paths.tsv').open(),delimiter='\t'))
        cone=list(csv.DictReader((d/'reply181-cone.tsv').open(),delimiter='\t'))
        assert len(xs)==24 and len(cone)==24
        assert {(x['from'],x['to']) for x in xs}=={(x['source'],x['destination']) for x in m['reply_selected']}
        assert all(abs(float(x['relationship'])-11.904)<.002 for x in xs)
        within=all(float(x['delay'])<9.904 and float(x['slack'])>=0 for x in xs)
        if not a.post_map:assert within,'routed capture budget failed'
        result=dict(scope_pass=True,post_map=a.post_map,rows=24,unique_reply_pairs=8,
            max_data_delay_ns=max(float(x['delay']) for x in xs),min_slack_ns=min(float(x['slack']) for x in xs),
            physical_pass=within if not a.post_map else None,full_design_pass=False,
            sources=m['sources'],checker_sha256=sha(Path(__file__)),script_sha256=sha(d/'check-reply181.tcl'))
        assert a.out and not a.out.exists();a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
        print(json.dumps({k:v for k,v in result.items() if k!='sources'}))

if __name__=='__main__':main()
