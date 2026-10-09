# SPDX-License-Identifier: MIT
"""Report new127 fitted clock minima without carrying over126 timing approval."""
from pathlib import Path
import argparse,csv,json,re,shutil,subprocess
from nes_loader127 import ROOT,put,sha
def inspect(o):
 report=(o/'output_files/live.fit.rpt').read_text(errors='replace')
 summary=(o/'output_files/live.fit.summary').read_text(errors='replace')
 assert 'Fitter Status : Successful' in summary
 def count(label):
  match=re.search(re.escape(label)+r'\s*[:;]\s*([\d,]+)',summary+'\n'+report);assert match,label
  return int(match[1].replace(',',''))
 resources={n:count(n) for n in ['Total logic elements','Total registers','Total pins','Total virtual pins','Total PLLs']}
 match=re.search(r'; Total LABs:  partially or completely used\s*;\s*([\d,]+) / 963',report);assert match
 resources['LAB']=int(match[1].replace(',',''));assert resources['LAB']<=963 and resources['Total logic elements']<=15408
 resources['M9K']=count('M9Ks')
 assert 'Ignored assignment' not in (o/'fit127.log').read_text(errors='replace')
 rows=list(csv.DictReader((o/'clock-pairs124.tsv').open(),delimiter='\t'))
 same={}
 for r in rows:
  if r['type']=='setup' and r['from_clock']==r['to_clock']:
   n=r['from_clock'];same[n]=min(same.get(n,1e9),float(r['slack']))
 assert len(same)==3,same
 raw=min(float(r['slack']) for r in rows)
 m=dict(resources=resources,same_clock_setup_min_ns=same,raw_clock_pair_min_ns=raw,clock_rows=len(rows),fit_passed=True,same_clock_setup_pass=all(v>=0 for v in same.values()),full_timing_pass=False,old126_data_constraints_reused=False,installable=False)
 return m
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--quartus-bin',type=Path,required=True);a=p.parse_args();o=a.out
 # Existing read-only audit selects clocks and local_memory, no old reader hierarchy.
 shutil.copy2(ROOT/'tools/nes_reset124_audit.tcl',o/'audit127.tcl')
 with (o/'audit127.log').open('wb') as log:r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t','audit127.tcl'],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 assert r.returncode==0
 put(o/'review127.json',json.dumps(inspect(o),indent=2)+'\n');print(json.dumps(inspect(o)))
if __name__=='__main__':main()
