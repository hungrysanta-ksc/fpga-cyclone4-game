# SPDX-License-Identifier: MIT
"""Target synthesis speed only at the measured SPI decoder and loader instances."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha

ASSIGNMENTS='''
# Keep area optimization for PPU/OAM; use speed only for measured command paths.
set_instance_assignment -name CYCLONEII_OPTIMIZATION_TECHNIQUE SPEED -to "core|loader_boot|control"
set_instance_assignment -name CYCLONEII_OPTIMIZATION_TECHNIQUE SPEED -to "core|loader_boot|boot|loader"
'''

def prepare(baseline,out):
    assert not out.exists() and str(out).isascii()
    v=json.loads((ROOT/'analysis/predecode165-verification.json').read_bytes())
    assert sha(baseline/'result.json')==v['raw_result_sha256']['map03']
    m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True)
    for n,h in m['sources'].items():
        assert sha(baseline/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
    p=out/'board.qsf';p.write_text(p.read_text()+ASSIGNMENTS,encoding='utf8')
    result=dict(baseline=m['sources'],sources={n:sha(out/n) for n in m['sources']},changed=['board.qsf'],public_sources={'tools/nes_speed165.py':sha(Path(__file__))})
    assert [n for n,h in result['sources'].items() if h!=result['baseline'][n]]==['board.qsf']
    (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.baseline,a.out)
