# SPDX-License-Identifier: MIT
"""Verify private075 evidence; user inputs/platform snapshots are not public."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(e):
 meta=json.loads((ROOT/'analysis/offline075-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files']
 assert len(files)==meta['evidence_files']
 assert set(files)=={p.relative_to(e).as_posix() for p in e.rglob('*') if p.is_file() and p!=e/'manifest.json'}
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
 for n,data in meta['received'].items():assert sha(e/'inputs'/n)==data['sha256'] and (e/'inputs'/n).stat().st_size==data['bytes'],n
 menu=json.loads((e/'menu-02/result.json').read_bytes());assert menu['results']=={'actual':{'checks':3,'exit':0},'guarded':{'checks':15,'exit':0}}
 assert not menu['physical'] and not menu['production_modified']
 assert 'current_gate=REJECT' in (e/'menu-02/actual.log').read_text()
 assert 'implicit-fallthrough' in (e/'menu-01/actual-compile.log').read_text()
 sd=json.loads((e/'sd-01/result.json').read_bytes());assert sd['edge_cases']==32 and not sd['physical']
 assert sd['current_cmd24_end_to_start_edges']==2 and sd['extra_eight_clocks_end_to_start_edges']==10
 assert (e/'sd-01/run.log').read_text().count('EDGE075 CMD')==32
 base=json.loads((e/'base-01/result.json').read_bytes());assert base['raw_bytes']==214981 and base['negative_controls']==13 and not base['hardware_execution']
 assert 'all_bytes=1' in (e/'base-01/programmer.log').read_text()
 assert not meta['firmware_changed'] and not meta['physical_success'] and not meta['nes_pair_installable']
 print('PASS075 frozen='+str(len(files))+' actual-menu3/host-guard15/edge32/base214981+13; hardware=0 firmware_changes=0')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);verify(p.parse_args().evidence)
