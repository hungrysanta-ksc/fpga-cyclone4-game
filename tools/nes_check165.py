# SPDX-License-Identifier: MIT
"""Keep CHECK retirement edges; avoid response gating a carry-chain input."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha

def transform(s,variant='counter-data'):
    old="check_next[7:0]<=check_next[7:0]+1'b1;check_next[18:8]<=check_next[18:8]+next_carry8;"
    assert s.count(old)==1
    terms=["check_next[0]<=~check_next[0];"]
    for i in range(1,8):terms.append(f"check_next[{i}]<=check_next[{i}] ^ (&check_next[{i-1}:0]);")
    terms.append('check_next[8]<=check_next[8] ^ next_carry8;')
    for i in range(9,19):terms.append(f"check_next[{i}]<=check_next[{i}] ^ (next_carry8 && (&check_next[{i-1}:8]));")
    s=s.replace(old,'\n        // Bitwise carry prefixes keep retirement control outside the arithmetic.\n        '+'\n        '.join(terms)+'\n       ')
    if variant in ['data-mux','counter-data']:
        needle='output reg [7:0] load_data,';assert s.count(needle)==1
        s=s.replace(needle,'(* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF" *) '+needle)
    else:assert variant=='prefix-only'
    if variant=='counter-data':
        needle='(* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF" *) reg [18:0] check_next;'
        assert s.count(needle)==1
        s=s.replace(needle,'(* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF; -name ALLOW_SYNCH_CTRL_USAGE OFF" *) reg [18:0] check_next;')
    return s

def prepare(baseline,out,variant='counter-data'):
    assert not out.exists() and str(out).isascii()
    pub=json.loads((ROOT/'analysis/oam-secondary165-verification.json').read_bytes())
    assert sha(baseline/'result.json')==pub['raw_result_sha256']['map03']
    m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True)
    for n,h in m['sources'].items():
        assert sha(baseline/n)==h,n
        d=out/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,d)
    p=out/'nes_rom_spi.sv';before=p.read_text();p.write_text(transform(before,variant),encoding='utf8')
    (out/'check.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),p.read_text().splitlines(True),fromfile='secondary165/nes_rom_spi.sv',tofile='check165/nes_rom_spi.sv')),encoding='utf8')
    result=dict(variant=variant,baseline=m['sources'],sources={n:sha(out/n) for n in m['sources']},changed=['nes_rom_spi.sv'],public_sources={'tools/nes_check165.py':sha(Path(__file__))})
    assert [n for n in m['sources'] if result['sources'][n]!=m['sources'][n]]==['nes_rom_spi.sv']
    (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--variant',choices=['prefix-only','data-mux','counter-data'],default='counter-data')
    a=p.parse_args();prepare(a.baseline,a.out,a.variant)
