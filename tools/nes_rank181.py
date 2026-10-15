# SPDX-License-Identifier: MIT
"""Isolated board181 candidate: compare sprite keys before rank selection.

The selected map03 and every unmodified source are checked by SHA256. No
protocol, storage, latency, clock, constraint or error predicate is changed.
"""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha
from nes_reject180 import replace

def compact(s):
    return replace(s,' wire same_object=rank_valid[rank] && rank_key[rank]==key;',
        ' // Compare locally: select eight verdict bits instead of eight 38-bit keys.\n'
        ' wire [7:0] rank_equal;\n'
        ' genvar rk;generate for(rk=0;rk<8;rk=rk+1)begin:key_compare\n'
        '  assign rank_equal[rk]=(rank_key[rk]==key);\n'
        ' end endgenerate\n'
        ' wire same_object=rank_valid[rank] && rank_equal[rank];')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    ref=ROOT/'analysis/board181-verification.json'
    sources=json.loads(ref.read_bytes())['verification']['fits']['map03']['sources']
    a.out.mkdir(parents=True)
    for n,h in sources.items():
        assert sha(a.baseline/n)==h,n
        dst=a.out/n;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(a.baseline/n,dst)
    f=a.out/'nes_native_compact181.sv'
    f.write_text(compact(f.read_text()),encoding='utf8',newline='\n')
    result=dict(sources={n:sha(a.out/n) for n in sources},
        changed=['nes_native_compact181.sv'],baseline_analysis_sha256=sha(ref),
        preparer_sha256=sha(Path(__file__)),hardware=False)
    (a.out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print('Prepared rank comparison candidate;',len(sources),'pinned sources')

if __name__=='__main__':main()
