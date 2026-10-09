# SPDX-License-Identifier: MIT
"""Recheck123 fitted evidence and limits, without rebuilding or editing archives."""
from pathlib import Path
import argparse,json,hashlib,csv,re
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inspect(o):
 r=json.loads((o/'result.json').read_bytes())
 assert r['phases']==dict(map=0,fit=0,sta=0)
 assert not r['installable'] and not r['loader_present'] and not r['guard_present']
 for n,h in r['sources'].items():assert sha(o/n)==h,n
 rows=list(csv.DictReader((o/'clock-pairs123.tsv').open(),delimiter='\t'))
 clocks=list(csv.DictReader((o/'clocks123.tsv').open(),delimiter='\t'))
 assert len(clocks)==4 and sorted(float(x['period']) for x in clocks)==[5.952,11.904,45.454,125.0]
 assert len(rows)==60 and len({x['corner'] for x in rows})==3
 same=[x for x in rows if x['from_clock']==x['to_clock']]
 cross=[x for x in rows if x['from_clock']!=x['to_clock']]
 assert min(float(x['slack']) for x in same)>=0
 assert any(float(x['slack'])<0 for x in cross) and not r['all_constrained_timing_pass']
 setup={}
 for c in clocks:
  values=[float(x['slack']) for x in same if x['type']=='setup' and x['from_clock']==c['name']]
  if values:setup[c['name']]=min(values)
 fit=(o/'output_files/live.fit.rpt').read_text(encoding='latin1');summary=(o/'output_files/live.fit.summary').read_text()
 labs=int(re.search(r'Total LABs:  partially or completely used\s*;\s*(\d+) / 963',fit)[1])
 le=int(re.search(r'Total logic elements : ([0-9,]+)',summary)[1].replace(',',''))
 m9k=int(re.search(r'; M9Ks\s*;\s*(\d+) / 56',fit)[1])
 return dict(clocks=clocks,rows=rows,same_clock_setup_min_ns=setup,raw_min_ns=min(float(x['slack']) for x in rows),LE=le,LAB=labs,remaining_LAB=963-labs,M9K=m9k)
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence
 root=Path(__file__).resolve().parents[1];m=json.loads((root/'analysis/clock123-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(root/n)==h,n
 old=inspect(e/'fit01');new=inspect(e/'fit02');assert new==m['final_audit']
 assert 'Missing location assignment' in (e/'fit01/output_files/live.fit.rpt').read_text(encoding='latin1')
 assert 'Missing location assignment' not in (e/'fit02/output_files/live.fit.rpt').read_text(encoding='latin1')
 r=json.loads((e/'fit02/result.json').read_bytes())
 pintext=(e/'fit02/output_files/live.pin').read_text();assigned={}
 for line in pintext.splitlines():
  cols=[v.strip() for v in line.split(':')]
  if len(cols)==7 and cols[-1]=='Y':assigned[cols[0]]=cols[1]
 assert len(r['physical_pin_assignments'])==46
 for line in r['physical_pin_assignments']:
  fields=line.split();assert assigned[fields[-1]]==fields[1].removeprefix('PIN_'),line
 assert 'Total pins : 46 / 166' in (e/'fit02/output_files/live.fit.summary').read_text()
 assert 'Total PLLs : 1 / 4' in (e/'fit02/output_files/live.fit.summary').read_text()
 for n,h in r['public_inputs'].items():assert sha(root/n)==h,n
 assert sha(e/'fit02/executed-driver.py')==sha(root/'tools/nes_clock_fit123.py')
 assert sha(e/'fit02/audit123.tcl')==sha(root/'tools/nes_clock_audit123.tcl')
 sdc=(e/'fit02/live.sdc').read_text();assert 'set_false_path' not in sdc and 'set_clock_groups' not in sdc
 comparison=json.loads((e/'core-source-comparison.json').read_bytes())
 assert set(comparison['different'])=={'ncr1_live_tb.sv','rom_backend_model.sv'}
 for n,v in comparison['common'].items():
  if n not in comparison['different']:assert sha(e/'fit02'/n)==v['122']==v['123'],n
 print('PASS123 archive/source pins; 46 located IO; PLL84/168; local timing passes but cross-clock/reset and external IO remain OPEN')
if __name__=='__main__':main()
