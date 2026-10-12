# SPDX-License-Identifier: MIT
"""Verify exact four QSF assignments, local fitted chains, and all-clock STA."""
from pathlib import Path
import argparse,csv,json
from nes_game147 import ROOT,sha
from nes_release165 import TARGETS,suffix
from check_nes_check165 import inspect
from check_nes_retire165 import nominal

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','reproduced']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();d=a.candidate;m=json.loads((d/'preparation.json').read_bytes())
 assert m==json.loads((a.reproduced/'preparation.json').read_bytes())
 pub=json.loads((ROOT/'analysis/eligibility165-verification.json').read_bytes())
 assert sha(a.baseline/'result.json')==m['baseline_result_sha256']==pub['raw_result_sha256']['map02']
 assert m['changed']==['board.qsf'] and m['targets']==TARGETS and len(m['sources'])==61
 for n,h in m['sources'].items():
  assert sha(d/n)==sha(a.reproduced/n)==h,n
  assert sha(a.baseline/n)==m['baseline'][n],n
  if n!='board.qsf':assert h==m['baseline'][n],n
 assert (d/'board.qsf').read_bytes()==(a.baseline/'board.qsf').read_bytes()+suffix().encode()
 for n in ['map.log','fit.log']:
  text=(d/n).read_text(errors='replace');assert 'Ignored assignment' not in text and 'Critical Warning' not in text,n
 assert sha(d/'release165-paths.tcl')==sha(ROOT/'tools/nes_release165_paths.tcl')
 def rows(name):return list(csv.DictReader((d/name).open(),delimiter='\t'))
 settings=rows('release165-settings.tsv');assert {r['target']:r['value'] for r in settings}==dict.fromkeys(TARGETS,'ON')
 top=rows('release165-topology.tsv');paths=rows('release165-paths.tsv');assert len(paths)==15
 fanout={}
 for chain in ['records','prepared']:
  first=[r for r in top if r['chain']==chain and r['stage']=='0'];assert len(first)==1
  assert first[0]['to']==first[0]['from'][:-2]+'1]',first
  fanout[chain]=len([r for r in top if r['chain']==chain and r['stage']=='1'])
  assert fanout[chain]>0
 stages={(r['chain'],r['stage']):r['from'] for r in top};assert len(set(stages.values()))==4
 assert all('audio|' not in name for name in stages.values())
 chain_min={k:min(float(r['slack']) for r in paths if r['group']!='held' and r['kind']==k) for k in ['setup','hold']}
 assert all(v>=0 for v in chain_min.values())
 host=json.loads((ROOT/'analysis/native-host165-verification.json').read_bytes())
 assert sha(d/'nes_native_mailbox165.sv')==host['public_sources']['src/nes/diagnostic/nes_native_mailbox165.sv']
 public={**m['public_sources']}
 for n in ['tools/check_nes_release165.py','tools/nes_release165_paths.tcl','tools/check_nes_check165.py','tools/check_nes_oam_port165.py','tools/check_nes_retire165.py','tools/check_nes_retire165_nominal.py','tools/nes_secondary165_timing.tcl','tools/nes_predecode165_paths.tcl']:
  public[n]=sha(ROOT/n)
 result={**inspect(d),'nominal':nominal(d),'baseline_nominal':nominal(a.baseline),
  'rtl_changed':False,'source_byte_reproduction':True,'unchanged_files':60,'qsf_assignments':settings,
  'release_registers':[dict(chain=k[0],stage=k[1],node=v) for k,v in stages.items()],
  'release_second_fanout':fanout,'release_chain_min_ns':chain_min,
  'release_to_held_setup_ns':min(float(r['slack']) for r in paths if r['group']=='held'),
  'functional_reuse':{'eligibility_public_sha256':sha(ROOT/'analysis/eligibility165-verification.json'),
   'connected':pub['sequential_summary'],'reader':pub['reader_terminal_equivalence'],
   'mailbox_source_sha256':sha(d/'nes_native_mailbox165.sv'),'mailbox_public_sha256':sha(ROOT/'analysis/native-host165-verification.json')},
  'scope':'Four merge-prevention assignments only. RTL and timing constraints byte-identical to eligibility165 map02; prior functional evidence reused, not rerun. Fitted local release chain topology and stage setup/hold verified, not full reset/CDC/MTBF/IO signoff or new gameplay.',
  'cartridge_sram_reserved':True,'hardware_package':False,'public_sources':public}
 assert not (d/'result.json').exists();(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['fit_le','used_labs','nominal','release_chain_min_ns','release_second_fanout','release_to_held_setup_ns']}))
if __name__=='__main__':main()
