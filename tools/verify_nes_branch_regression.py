"""Preserve integrated video/IRQ semantics after branch bus correction. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,hashlib,json
from verify_nes_irq_phase import parse_rtl,parse_mesen,compare

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('rtl','baseline','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();integration=json.loads((a.rtl/'verification.json').read_text());assert integration['passed']
 names=['control.tsv','edges.tsv','fetch.tsv','frames.tsv']+[f'frame-{i:3d}.hex' for i in range(1,5)]
 identical={n:sha(a.rtl/n)==sha(a.baseline/n) for n in names}
 rtl=parse_rtl(a.rtl/'cpu-phase.tsv');mesen=parse_mesen(a.mesen/'cpu-phase.tsv');phase=compare(rtl,mesen)
 cart=[r for r in rtl if r['cart']];observations=[]
 for i,r in enumerate(cart):
  if r['counter'] in [3,4,5,6] and r['line']==62 and r['dot']<250 and r['address']==0xe184 and r['read']:
   bus=cart[i:i+4];assert [b['address'] for b in bus]==[0xe184,0xe185,0xe186,0xe182]
   assert [b['data'] for b in bus]==[0xf0,0xfc,0xa9,0xa5] and all(b['read'] for b in bus)
   matches=[m for m in mesen if m['counter']==r['counter'] and m['address']==0xe186 and m['line']==62 and m['dot']==bus[2]['dot']+4]
   assert len(matches)==1 and matches[0]['data']==bus[2]['data']
   observations.append(dict(counter=r['counter'],rtl_branch_dot=r['dot'],rtl_dummy_dot=bus[2]['dot'],mesen_dummy_dot=matches[0]['dot'],address=bus[2]['address'],data=bus[2]['data']))
 assert len(observations)>=8
 result=dict(candidate='NES-P2-BRANCH-011',passed=integration['passed'] and phase['passed'] and all(identical.values()),prior_integrated_files_identical=identical,integration=integration,irq_relative_cycles=phase,corrected_polling_reads=observations,verifier_sha256=sha(Path(__file__)),scope='Original Mapper4 regression under ideal memory; common counter3..6 retain the pre-existing four-dot phase offset. No direct IRQ assertion-to-entry equivalence, exhaustive interrupt sampling, full CPU or hardware conformance claim.')
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('PASS' if result['passed'] else 'FAIL','integrated/IRQ regression;',len(observations),'corrected polling discarded reads');raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
