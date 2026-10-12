# SPDX-License-Identifier: MIT
"""Keep four existing host-domain mailbox release registers local; no RTL change."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha

TARGETS=[f'core|{inst}|{reg}[{bit}]' for inst,reg in [('native_records','dr'),('native_prepared','sr')] for bit in [0,1]]
def suffix():
    return '\n# Keep the existing host release chains local; no new latency or timing exceptions.\n'+''.join(f'set_instance_assignment -name DONT_MERGE_REGISTER ON -to {n}\n' for n in TARGETS)

def prepare(baseline,out):
    assert not out.exists() and str(out).isascii()
    pub=json.loads((ROOT/'analysis/eligibility165-verification.json').read_bytes())
    assert sha(baseline/'result.json')==pub['raw_result_sha256']['map02']
    m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True)
    for n,h in m['sources'].items():
        assert sha(baseline/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
    (out/'board.qsf').write_bytes((baseline/'board.qsf').read_bytes()+suffix().encode())
    sources={n:sha(out/n) for n in m['sources']}
    assert [n for n,h in sources.items() if h!=m['sources'][n]]==['board.qsf']
    r=dict(sources=sources,baseline=m['sources'],targets=TARGETS,rtl_changed=False,changed=['board.qsf'],
           baseline_result_sha256=sha(baseline/'result.json'),public_sources={'tools/nes_release165.py':sha(Path(__file__))})
    (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.baseline,a.out)
