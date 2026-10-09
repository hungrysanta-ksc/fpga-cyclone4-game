# SPDX-License-Identifier: MIT
"""Reuse124 routed DB; exact bundled pairs, no clock-group waivers."""
from pathlib import Path
import argparse,json,csv,re,hashlib,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,s):p.write_text(s,encoding='utf8',newline='\n')
BUDGETS={'reader_address':4.0,'reader_data':40.0,'bridge_request':40.0,'bridge_reply':10.0}
PERIODS={'reader_address':5.952,'reader_data':45.454,'bridge_request':45.454,'bridge_reply':11.904}
def classify(x):
 s,d=x['from'],x['to'];b='nes_transport:transport|nes_packet_cdc_ram:bridge|'
 if s.startswith('nes_rom_early:rom_service|pending_address[') and re.fullmatch(r'nes_rom_physical:physical\|(psram_address\[\d+\]|chip|lane)',d):return 'reader_address'
 if s.startswith('nes_rom_physical:physical|data_hold[') and d.startswith(('nes_probe:','nes_rom_early:')):return 'reader_data'
 if s.startswith(b) and re.fullmatch(r'req_(op|epoch|seq|address)\[\d+\]',s[len(b):]) and d.startswith(b+'q_'):return 'bridge_request'
 if s.startswith(b+'reply_') and d.startswith(b+'rsp_'):return 'bridge_reply'
 if d.endswith(('request_sync[0]','ack_sync[0]','req_sync[0]','queue_up_h[0]','host_up_q[0]')):return 'control_first_stage'
 raise AssertionError(('unclassified CDC',s,d))
def inventory(path):
 rows=list(csv.DictReader(path.open(),delimiter='\t'));assert len(rows)==1218
 groups={k:[] for k in [*BUDGETS,'control_first_stage']}
 for x in rows:groups[classify(x)].append(x)
 assert len({(x['from'],x['to']) for x in rows})==378
 assert len(groups['control_first_stage'])==18
 return rows,groups
def main():
 p=argparse.ArgumentParser()
 for n in ['evidence124','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.evidence124;o=a.out.resolve();assert not o.exists() and str(o).isascii()
 old=json.loads((ROOT/'analysis/reset124-verification.json').read_bytes());assert sha(e/'manifest.json')==old['manifest_sha256']
 for n,h in json.loads((e/'manifest.json').read_bytes())['files'].items():
  if n.startswith('fit01/'):assert sha(e/n)==h,n
 shutil.copytree(e/'fit01',o)
 shutil.copy2(__file__,o/'executed-sta125.py');shutil.copy2(ROOT/'tools/nes_cdc125_inventory.tcl',o/'inventory125.tcl')
 def run(script,label):
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t',script],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  assert r.returncode==0,label
 run('inventory125.tcl','inventory125');rows,groups=inventory(o/'inventory125.tsv')
 spec={};sdc=['# Same124 DB only; no datapath_only support in this Quartus.', 'proc exact125 {name} {', ' set r [get_registers $name]', ' if {[get_collection_size $r]!=1} {error "Missing/ambiguous register $name"}', ' foreach_in_collection n $r {if {[get_node_info -name $n] ne $name} {error "Register mismatch $name"}}', ' return $r','}']
 pairs=[]
 for group,budget in BUDGETS.items():
  xs=groups[group];ps=sorted({(x['from'],x['to']) for x in xs})
  assert budget<PERIODS[group] and max(float(x['delay']) for x in xs)<budget
  # Data-only budget and SDC clock-relative maximum are different checks.
  # One destination period is derived from the two-stage capture contract,
  # leaving a further period before the earliest functional capture.
  limit=PERIODS[group]
  spec[group]=dict(budget_ns=budget,sdc_max_delay_ns=limit,destination_period_ns=PERIODS[group],conditional_capture_min_ns=2*PERIODS[group],max_data_delay_ns=max(float(x['delay']) for x in xs),rows=len(xs),pairs=len(ps))
  for src,dst in ps:
   sdc.append(f'set_max_delay -from [exact125 {{{src}}}] -to [exact125 {{{dst}}}] {limit}')
   pairs.append((group,src,dst,limit))
 put(o/'bundled125.sdc','\n'.join(sdc)+'\n')
 put(o/'pairs125.tcl','set pairs125 {\n'+''.join(f' {{{g} {{{s}}} {{{d}}} {v}}}\n' for g,s,d,v in pairs)+'}\n')
 script='''package require ::quartus::sta
project_open live
create_timing_netlist
read_sdc
source bundled125.sdc
source pairs125.tcl
set out [open constrained125.tsv w]
puts $out "corner\\tgroup\\tfrom\\tto\\tslack\\tdelay"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach row $pairs125 {
  lassign $row group src dst budget
  set ps [get_timing_paths -setup -from [exact125 $src] -to [exact125 $dst] -npaths 1]
  if {[get_collection_size $ps]!=1} {error "Absent pair $src $dst"}
  foreach_in_collection p $ps {puts $out "$corner\\t$group\\t$src\\t$dst\\t[get_path_info -slack $p]\\t[get_path_info -data_delay $p]"}
  if {$group eq "reader_address" && $dst eq "nes_rom_physical:physical|chip"} {
   report_timing -setup -from [exact125 $src] -to [exact125 $dst] -npaths 1 -detail full_path -file address-$corner.rpt
  }
 }
}
close $out
report_exceptions -file exceptions125.rpt
report_ucp -file unconstrained125.rpt
delete_timing_netlist
project_close
'''
 put(o/'constraints125.tcl',script);run('constraints125.tcl','constraints125')
 bounded=list(csv.DictReader((o/'constrained125.tsv').open(),delimiter='\t'));assert len(bounded)==len(pairs)*3
 assert min(float(x['slack']) for x in bounded)>0
 for g in spec:spec[g]['constrained_min_slack_ns']=min(float(x['slack']) for x in bounded if x['group']==g)
 result=dict(candidate='NES-BUNDLED-CDC-125',passed=True,fit_reused=True,groups=spec,constrained_pairs=len(pairs),constrained_rows=len(bounded),raw_rows=len(rows),raw_min_slack_ns=min(float(x['slack']) for x in rows),unexcepted_controls=groups['control_first_stage'],full_timing_pass=False,external_io_signoff=False,installable=False,scope='Conditional bundled-data budgets with actual routed endpoints. Data-delay checks exclude clock networks; set_max_delay checks include them. First-stage asynchronous controls/reset/MTBF/external IO not signed off.')
 put(o/'result125.json',json.dumps(result,indent=2)+'\n');print(json.dumps(spec,indent=2))
if __name__=='__main__':main()
