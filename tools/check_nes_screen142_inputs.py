# SPDX-License-Identifier: MIT
"""Audit the five new external-input synchronizers on selected routing."""
from pathlib import Path
import argparse,csv,json,shutil,subprocess
from nes_spi_boot import ROOT

def main():
 p=argparse.ArgumentParser()
 for n in ['fit','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();shutil.copytree(a.fit,a.out)
 prefix='nes_screen_status142:screen_status|'
 names=['wr_sync','rd_sync','ss_sync','sck_sync','mosi_sync']
 chains='set chains126 {\n'+''.join(f' {{input {n} {{{prefix}{n}[0]}} {{{prefix}{n}[1]}}}}\n' for n in names)+'}\n'
 script=(ROOT/'tools/nes_control126.tcl').read_text().replace('project_open live','project_open board').replace('source chains126.tcl',chains)
 (a.out/'inputs142.tcl').write_text(script,encoding='utf8',newline='\n')
 with (a.out/'inputs142.log').open('wb') as f:r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t','inputs142.tcl'],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
 assert r.returncode==0
 def rows(n):return list(csv.DictReader((a.out/n).open(),delimiter='\t'))
 top=rows('topology126.tsv');tim=rows('timing126.tsv')
 for n in names:
  first=[x for x in top if x['chain']==n and x['stage']=='0']
  assert len(first)==1 and first[0]['to']==prefix+n+'[1]',n
 assert len(tim)==30 and min(float(x['slack']) for x in tim)>0
 result=dict(passed=True,chains=5,paths=30,first_stage_fanout=1,setup_min_ns=min(float(x['slack']) for x in tim if x['type']=='setup'),hold_min_ns=min(float(x['slack']) for x in tim if x['type']=='hold'),mtbf_calculated=False,physical_input_timing_measured=False,scope='External write/read/SPI control chains only. Address/data use qualified stable samples; raw vector flags are diagnostic evidence, not control or guaranteed pulse capture.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
