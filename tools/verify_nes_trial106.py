# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json
from nes_spi_boot import ROOT,sha
from assess_nes_trial106 import envelope

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 m=json.loads((ROOT/'analysis/trial106-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h==sha(e/'public-sources'/n),n
 assert sha(e/'envelope01/executed-assess106.py')==m['public_sources']['tools/assess_nes_trial106.py']
 r=json.loads((e/'envelope01/result.json').read_bytes());b=json.loads((e/'envelope01/budget.json').read_bytes())
 for n,v in envelope(b).items():assert r[n]==v,n
 assert r['normal_and_outside_exact_reproduction'] and len(r['invalid_inputs_rejected'])==4
 policy=json.loads((ROOT/'docs/nes-trial106-decision.json').read_bytes())
 assert policy['hardware_trial_approved'] is False and policy['observation_limit_seconds']==600
 assert len(policy['open_conditions'])==2 and policy['observation_limit_is_mcu_guarantee'] is False
 assert not m['physical'] and not m['installable'] and not m['new_arm']
 print('PASS106 frozen external envelope and observation policy; two physical conditions remain open')
if __name__=='__main__':main()
