# SPDX-License-Identifier: MIT
"""Classify current135 crossings; constrain only identified held-data pairs."""
from pathlib import Path
import argparse,csv,json,re,shutil,subprocess
from nes_cdc125_sta import ROOT,sha,put,BUDGETS as OLD_BUDGETS,PERIODS as OLD_PERIODS
BUDGETS={k:OLD_BUDGETS[k] for k in ['reader_address','reader_data']}
PERIODS={k:OLD_PERIODS[k] for k in BUDGETS}
RD='nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_physical:reader|'
LD='nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_loader:loader|'
BR='nes_live_joint:core|nes_transport:transport|nes_packet_cdc_ram:bridge|'
GU='nes_live_joint:core|nes_diag_clock_guard127:clock_guard|'
CONTROL={RD+'request_sync[0]',RD+'ack_sync[0]',GU+'ref_sync[0]',GU+'mem_sync[0]'}
LIFECYCLE={LD+'state.RUN',LD+'fault',LD+'release_reset[1]','nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|check_failed','nes_live_joint:core|nes_domain_reset124:diagnostic_release|release_reset[1]'}
def rows(p):return list(csv.DictReader(p.open(),delimiter='\t'))
def classify(x):
 s,d=x['from'],x['to']
 if s.startswith(RD+'address_hold[') and re.fullmatch(re.escape(RD)+r'(lane|chip|check_response_address\[\d+\])',d):return 'reader_address'
 if s.startswith(RD+'data_hold[') and d.startswith(('nes_live_joint:core|nes_probe:','nes_live_joint:core|nes_rom_early:')):return 'reader_data'
 if s.startswith(BR) and re.fullmatch(r'req_(op|epoch|seq|address)\[\d+\]',s[len(BR):]) and d.startswith(BR+'q_'):return 'bridge_request'
 if s.startswith(BR+'reply_') and d.startswith(BR+'rsp_'):return 'bridge_reply'
 if d in CONTROL:return 'control_first_stage'
 if s==LD+'chr32':return 'configuration_open'
 if s in LIFECYCLE and d.startswith(RD):return 'lifecycle_open'
 raise AssertionError(('Unclassified current crossing',s,d))
def inventory(p):
 xs=rows(p);g={k:[] for k in [*BUDGETS,'control_first_stage','configuration_open','lifecycle_open']}
 for x in xs:g[classify(x)].append(x)
 assert len(xs)==2400 and len({(x['from'],x['to']) for x in xs})==505
 assert {x['to'] for x in g['control_first_stage']}==CONTROL
 assert {x['from'] for x in g['lifecycle_open']}==LIFECYCLE
 return xs,g
def main():
 p=argparse.ArgumentParser();p.add_argument('--inventory',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--quartus-bin',type=Path,required=True)
 a=p.parse_args();o=a.out.resolve();assert not o.exists() and str(o).isascii()
 shutil.copytree(a.inventory,o);shutil.copy2(__file__,o/'executed-sta136.py')
 xs,groups=inventory(o/'inventory136.tsv');pairs=[];spec={}
 sdc=['# Conditional held-data checks on selected135 routing; no false paths.', 'proc exact136 {name} {',' set r [get_registers $name]',' if {[get_collection_size $r]!=1} {error "Missing/ambiguous register $name"}',' foreach_in_collection n $r {if {[get_node_info -name $n] ne $name} {error "Register mismatch $name"}}',' return $r','}']
 for g,rs in groups.items():
  ps=sorted({(x['from'],x['to']) for x in rs})
  spec[g]=dict(rows=len(rs),pairs=len(ps),max_data_delay_ns=max(float(x['delay']) for x in rs),raw_min_slack_ns=min(float(x['slack']) for x in rs))
  if g not in BUDGETS:continue
  assert spec[g]['max_data_delay_ns']<BUDGETS[g]<PERIODS[g]
  spec[g].update(budget_ns=BUDGETS[g],sdc_max_delay_ns=PERIODS[g],conditional_capture_min_ns=2*PERIODS[g])
  for s,d in ps:
   pairs.append((g,s,d,PERIODS[g]));sdc.append(f'set_max_delay -from [exact136 {{{s}}}] -to [exact136 {{{d}}}] {PERIODS[g]}')
 put(o/'classification136.tsv','group\t'+'\t'.join(xs[0])+'\n'+''.join(classify(x)+'\t'+'\t'.join(x.values())+'\n' for x in xs))
 put(o/'bundled136.sdc','\n'.join(sdc)+'\n')
 put(o/'pairs136.tcl','set pairs136 {\n'+''.join(f' {{{g} {{{s}}} {{{d}}} {v}}}\n' for g,s,d,v in pairs)+'}\n')
 # Reuse the generic exact-pair STA collector, not old endpoint classification.
 source=(ROOT/'tools/nes_cdc125_sta.py').read_text();script=source.split("script='''",1)[1].split("'''",1)[0]
 script=script.replace('project_open live','project_open board').replace('125','136').replace('\\t','\t').replace('nes_rom_physical:physical|chip',RD+'chip')
 put(o/'constraints136.tcl',script)
 def run(n):
  with (o/(n+'.log')).open('wb') as f:r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t',n+'.tcl'],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=600)
  assert r.returncode==0,n
 run('constraints136');bounded=rows(o/'constrained136.tsv');assert len(bounded)==3*len(pairs)
 for g in BUDGETS:
  spec[g]['constrained_min_slack_ns']=min(float(x['slack']) for x in bounded if x['group']==g)
  assert spec[g]['constrained_min_slack_ns']>0,g
 # Enumerate real fitted local-release registers, including hierarchy changes.
 ctl='set chains136 {\n'+''.join(f' {{control c{i} {{{n}}} {{{n[:-2]}1]}}}}\n' for i,n in enumerate(sorted(CONTROL)))+'}\n'
 ctl+='''set chainfile [open chains136.tsv w]
puts $chainfile "kind\\tchain\\tfirst\\tsecond"
set i 0
foreach_in_collection reg [get_registers *] {
 set name [get_node_info -name $reg]
 if {[regexp {\\|(release_reset|memory_reset|source_reset)\\[0\\]$} $name]} {
  set second [string replace $name end-1 end-1 1]
  lappend chains136 [list release r$i $name $second]
  incr i
 }
}
foreach row $chains136 {puts $chainfile [join $row "\\t"]}
close $chainfile
'''
 script=(ROOT/'tools/nes_control126.tcl').read_text().replace('project_open live','project_open board').replace('126','136').replace('source chains136.tcl',ctl)
 put(o/'control136.tcl',script);run('control136')
 chains=rows(o/'chains136.tsv');top=rows(o/'topology136.tsv');tim=rows(o/'timing136.tsv');local=rows(o/'local-reset136.tsv')
 for x in chains:
  first=[v for v in top if v['chain']==x['chain'] and v['stage']=='0']
  assert len(first)==1 and first[0]['to']==x['second'],x
 assert len(tim)==len(chains)*6 and min(float(x['slack']) for x in tim)>0
 summary=dict(candidate='NES-CDC-REFRESH-136',passed=True,groups=spec,raw_rows=len(xs),raw_pairs=505,constrained_pairs=len(pairs),constrained_rows=len(bounded),chains=len(chains),release_chains=sum(x['kind']=='release' for x in chains),chain_paths=len(tim),chain_min_setup_ns=min(float(x['slack']) for x in tim if x['type']=='setup'),chain_min_hold_ns=min(float(x['slack']) for x in tim if x['type']=='hold'),local_reset_rows=len(local),local_reset_min_ns=min(float(x['slack']) for x in local),local_reset_pass=all(float(x['slack'])>=0 for x in local),new_fit=False,full_timing_pass=False,mtbf_signoff=False,external_io_signoff=False,installable=False)
 put(o/'sta136.json',json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
