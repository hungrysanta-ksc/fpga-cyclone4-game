# SPDX-License-Identifier: MIT
"""Read-only124 evidence verification; simulations/fit are not rerun."""
from pathlib import Path
import argparse,csv,json,re,tempfile,shutil
from nes_reset124 import ROOT,sha,reader,bridge,transport,top
from nes_safe_reader122 import compare

def inspect_fit(o):
 r=json.loads((o/'result.json').read_bytes())
 assert r['phases']==dict(map=0,fit=0,sta=0)
 assert not any(r[k] for k in ['installable','loader_present','guard_present','all_constrained_timing_pass'])
 for n,h in r['sources'].items():assert sha(o/n)==h,n
 rows=list(csv.DictReader((o/'clock-pairs124.tsv').open(),delimiter='\t'))
 assert len(rows)==72 and len({x['corner'] for x in rows})==3
 local=[x for x in rows if x['from_clock']==x['to_clock']]
 assert min(float(x['slack']) for x in local)>0
 setup={c:min(float(x['slack']) for x in local if x['type']=='setup' and x['from_clock']==c) for c in sorted({x['from_clock'] for x in local})}
 resets=list(csv.DictReader((o/'reset-paths124.tsv').open(),delimiter='\t'))
 assert len(resets)==1272
 expected={f'{n}[{i}]' for n in ['nes_domain_reset124:core_release|release_reset','nes_rom_physical:physical|memory_reset','nes_transport:transport|nes_domain_reset124:host_release|release_reset'] for i in [0,1]}
 reset_only=[x for x in resets if x['type'] in ('recovery','removal')]
 assert {x['to'] for x in reset_only}==expected
 assert len(reset_only)==36
 for x in resets:
  assert x['from']=='nes_local_memory:local_memory|init_done'
  if x['type'] in ('setup','hold'):assert x['to'].startswith(('nes_probe:','nes_local_memory:')),x
  else:assert x['to'] in expected,x
 sdc=(o/'live.sdc').read_text();assert 'set_false_path' not in sdc and 'set_clock_groups' not in sdc
 fit=(o/'output_files/live.fit.rpt').read_text(encoding='latin1');summary=(o/'output_files/live.fit.summary').read_text(encoding='latin1')
 assert 'Missing location assignment' not in fit
 assert 'Total pins : 46 / 166' in summary and 'Total PLLs : 1 / 4' in summary
 assigned={}
 for line in (o/'output_files/live.pin').read_text().splitlines():
  cols=[x.strip() for x in line.split(':')]
  if len(cols)==7 and cols[-1]=='Y':assigned[cols[0]]=cols[1]
 for line in r['physical_pin_assignments']:
  fields=line.split();assert assigned[fields[-1]]==fields[1].removeprefix('PIN_')
 assert len(r['physical_pin_assignments'])==46
 return dict(LE=int(re.search(r'Total logic elements : ([0-9,]+)',summary)[1].replace(',','')),LAB=int(re.search(r'Total LABs:  partially or completely used\s*;\s*(\d+) / 963',fit)[1]),M9K=int(re.search(r'; M9Ks\s*;\s*(\d+) / 56',fit)[1]),same_clock_setup_min_ns=setup,raw_min_ns=min(float(x['slack']) for x in rows),clock_pair_rows=len(rows),init_done_path_rows=len(resets),reset_endpoints=sorted(expected),reset_recovery_removal_rows=len(reset_only),physical_pins=46,virtual_pins=264)

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence
 meta=json.loads((ROOT/'analysis/reset124-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==meta['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
 for label,driver in [('fit01','fit'),('unit01','unit'),('core01','core'),('transport04','transport')]:
  o=e/label;r=json.loads((o/'result.json').read_bytes())
  for n,h in r['sources'].items():assert sha(o/n)==h,(label,n)
  if driver=='core':
   # Metadata prose correction after execution; retained archived driver bytes.
   executed=(o/'executed-driver.py').read_text().replace('unchanged CF86','reset124 CF86').replace('unchangedCF86','reset124 CF86')
   assert executed==(ROOT/f'tools/nes_reset124_{driver}.py').read_text()
  else:assert sha(o/'executed-driver.py')==sha(ROOT/f'tools/nes_reset124_{driver}.py')
  assert sha(o/'executed-reset124.py')==sha(ROOT/'tools/nes_reset124.py')
 assert inspect_fit(e/'fit01')==meta['fit']
 assert sha(e/'fit01/audit124.tcl')==sha(ROOT/'tools/nes_reset124_audit.tcl')
 old=json.loads((ROOT/'analysis/clock123-verification.json').read_bytes())
 assert not old['full_timing_pass']
 for n,fn in [('nes_rom_physical.sv',reader),('nes_packet_cdc_ram.sv',bridge),('nes_transport.sv',transport),('nes_live_joint.sv',top)]:
  assert sha(e/'oracle123'/n)==meta['oracle123'][n]
  assert (e/'fit01'/n).read_text()==fn((e/'oracle123'/n).read_text()),n
 for n in ['nes_rom_physical.sv','nes_packet_cdc_ram.sv','nes_transport.sv','nes_domain_reset124.sv']:
  assert sha(e/'fit01'/n)==sha(e/'core01'/n),n
 assert sha(e/'fit01/nes_rom_physical.sv')==sha(e/'unit01/nes_rom_physical.sv')
 for n in ['nes_packet_queue_ram.sv','nes_packet_cdc_ram.sv','nes_host_stage.sv','nes_snes_frontend.sv','nes_transport.sv','nes_domain_reset124.sv']:assert sha(e/'fit01'/n)==sha(e/'transport04'/n)
 unit=json.loads((e/'unit01/result.json').read_bytes())
 assert unit['passed'] and unit['negative110_rejected'] and unit['negative_hold_rejected']
 assert [x['phase_ps'] for x in unit['cases']]==list(range(0,6000,375))
 assert sum(x['completed'] for x in unit['cases'])==8400 and sum(x['canceled'] for x in unit['cases'])==208
 assert '** Fatal: PHYSICAL check' in (e/'unit01/late110.log').read_text()
 assert '** Fatal: SAFE122 hold interval' in (e/'unit01/negative-no-hold.log').read_text()
 tr=json.loads((e/'transport04/result.json').read_bytes())
 assert tr['passed'] and tr['raw_bypass_rejected'] and len(tr['runs'])==6
 assert '** Fatal: RESET124 contract' in (e/'transport04/negative-bypass.log').read_text()
 assert 'latency bound' in (e/'transport02/frontend.log').read_text()
 assert 'got09 expected00000008' in (e/'transport03/frontend.log').read_text()
 assert tr['runs']['baseline-frontend']['pass']
 core=json.loads((e/'core01/result.json').read_bytes());assert core['passed'] and len(core['cases'])==1
 case=core['cases'][0];assert case==meta['core_case'] and case['case']=='fine_x' and case['phase_ns']==3.5
 history=json.loads((ROOT/'analysis/rom-physical-artifacts.json').read_bytes());prefix='analysis/local-rom-physical-052/live/'
 pins={v['path'][len(prefix):]:v['sha256'] for rows in history.values() if isinstance(rows,list) for v in rows if isinstance(v,dict) and v.get('path','').startswith(prefix)}
 with tempfile.TemporaryDirectory(prefix='nes-verify124-') as tmp:
  work=Path(tmp);shutil.copytree(e/'core01/phase03500/fine_x',work/'fine_x')
  for n,v in compare(work,e/'oracle052','fine_x',pins).items():assert case[n]==v,n
 assert not meta['installable'] and not meta['full_timing_pass']
 print('PASS124 domain reset wiring, 16phase reader, bridge/frontend/reset contracts,4coreframes,46pins/localSTA; bundled CDC/IO remain OPEN')
if __name__=='__main__':main()
