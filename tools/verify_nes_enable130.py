# SPDX-License-Identifier: MIT
"""Verify130 selected mapping, unchanged behavior and rejected experiment."""
from pathlib import Path
import argparse,csv,hashlib,json,tempfile
from nes_enable130 import ROOT,sha,materialize
from review_nes_enable130 import inspect

ATTRIBUTE=b'(* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF" *) '

def rows(p):
 return list(csv.DictReader(p.open(),delimiter='\t'))

def ports(p):
 r=rows(p/'state130-edges.tsv')
 assert len({x['register'] for x in r})==16
 enabled=[x['register'] for x in r if x['source'].endswith('|ena')]
 return dict(state=sum('|state.' in x for x in enabled),counter=sum('|remaining[' in x for x in enabled))

def review(e):
 baseline=e/'baseline02';a=e/'fit01';b=e/'fit02'
 bp=json.loads((baseline/'baseline130.json').read_bytes())
 prior=json.loads((ROOT/'analysis/reader129-verification.json').read_bytes())
 assert bp['source_manifest']==prior['manifest_sha256'] and not bp['new_fit']
 results={}
 for name,expected_attributes in [('fit01',1),('fit02',2)]:
  d=e/name;m=json.loads((d/'materialization130.json').read_bytes())
  for n,h in m['inputs'].items():
   assert h==bp['inputs'][n]==sha(baseline/n),n
   data=(d/n).read_bytes()
   if n=='nes_rom_loader.sv':
    assert data.count(ATTRIBUTE)==expected_attributes
    assert data.replace(ATTRIBUTE,b'')==(baseline/n).read_bytes()
   else:assert sha(d/n)==h,n
   assert sha(d/n)==m['outputs'][n],n
  assert json.loads((d/'fit130.json').read_bytes())['phases']==[dict(phase=x,returncode=0) for x in ['map','fit','sta']]
  meta=json.loads((d/'review130.json').read_bytes());core=inspect(d)
  assert {k:meta[k] for k in core}==core
  results[name]=core
 assert ports(baseline)==dict(state=4,counter=3)
 assert ports(a)==dict(state=0,counter=3)
 assert ports(b)==dict(state=0,counter=0)
 assert sha(a/'executed-nes_enable130.py')==sha(ROOT/'tools/nes_enable130.py')
 assert sha(a/'executed-nes_enable130_fit.py')==sha(ROOT/'tools/nes_enable130_fit.py')
 assert sha(a/'state130.tcl')==sha(ROOT/'tools/nes_enable130_paths.tcl')
 meta=json.loads((a/'review130.json').read_bytes())
 paths=rows(a/'state130-timing.tsv');p=meta['loader_ports']
 assert p['reported_paths']==len(paths)
 for kind in ['setup','hold']:
  assert p['minimum_'+kind+'_ns']==min(float(x['slack']) for x in paths if x['type']==kind)
 assert p['state_enable_inputs']==0 and p['enable_inputs']==3
 owner=rows(a/'reader129-paths.tsv')
 assert sum(x['group']=='old_direct' and x['paths']=='0' for x in owner)==3
 o=[x for x in owner if x['group'] in ['release_owner','owner_address','owner_input']]
 assert len(o)==219 and min(float(x['slack']) for x in o)==.950
 top=rows(a/'topology126.tsv');first=[x for x in top if x['stage']=='0']
 assert len(first)==1 and first[0]['to'].endswith('release_reset[1]')
 times=rows(a/'timing126.tsv');assert len(times)==6 and min(float(x['slack']) for x in times)==.383
 # Reproduce the public materializer without fitting. Its complete source
 # and constraint inventory must match the selected executed candidate.
 with tempfile.TemporaryDirectory(prefix='nes-enable130-identity-') as temp:
  d=Path(temp);materialize(d,e.parents[1],full=True)
  expected=json.loads((a/'materialization130.json').read_bytes())['outputs']
  actual=json.loads((d/'materialization130.json').read_bytes())['outputs']
  assert actual==expected
 return dict(selected='fit01',selected_review=meta,rejected_fit02=results['fit02'],baseline_enable_ports=ports(baseline),selected_enable_ports=ports(a),rejected_enable_ports=ports(b),behavioral_source_identical_to129=True,prior129_manifest=prior['manifest_sha256'],new_functional_simulation=False,new_asm_arm_package=False,full_timing_pass=False,installable=False)

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 m=json.loads((ROOT/'analysis/enable130-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 assert review(e)==m['checks'];print('PASS130 source identity, actual enable ports and timing; full timing still fails')
if __name__=='__main__':main()
