# SPDX-License-Identifier: MIT
"""Bind the minimal A5+READY candidate, differential/SPI tests and routed STA."""
from pathlib import Path
import argparse,json,csv
from nes_game147 import ROOT,sha
from nes_snapshot175 import CHANGED,transform as snapshot
from nes_ready175 import transform
from check_nes_check165 import inspect
from check_nes_retire165 import nominal

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','candidate','test','spi','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();load=lambda p:json.loads(p.read_bytes())
    base=load(ROOT/'analysis/errorzero174-verification.json')['sources']
    m=load(a.candidate/'preparation.json');assert m['baseline']==base
    for n,h in m['sources'].items():
        assert sha(a.baseline/n)==base[n] and sha(a.candidate/n)==h,n
        if n=='nes_rom_loader.sv':assert (a.candidate/n).read_text()==transform((a.baseline/n).read_text())
        elif n in CHANGED:assert (a.candidate/n).read_text()==snapshot(n,(a.baseline/n).read_text())
        else:assert h==base[n],n
    changed=sorted(n for n,h in m['sources'].items() if h!=base[n])
    assert changed==sorted(CHANGED+['nes_rom_loader.sv'])
    t=load(a.test/'result.json');spi=load(a.spi/'result.json')
    assert t['passed'] and t['states']==294912 and t['sequences']==1056 and t['reset_offsets']==19 and len(t['negatives'])==2
    assert t['source_sha256']==m['sources']['nes_rom_loader.sv'] and t['reference_sha256']==base['nes_rom_loader.sv']
    # Test copy uses host newline translation; compare text and retain its raw
    # bytes separately in the evidence manifest instead of claiming byte identity.
    assert (a.test/'candidate.sv').read_text()==(a.candidate/'nes_rom_loader.sv').read_text()
    assert sha(a.test/'bench.sv')==t['bench_sha256']
    assert spi['passed'] and spi['wire_bits']==14016
    for n,h in spi['sources'].items():
        assert sha(a.spi/n)==h,n
        if n in m['sources']:assert h==m['sources'][n],n
    paths=list(csv.DictReader((a.candidate/'ready175-paths.tsv').open(),delimiter='\t'))
    assert len(paths)==3 and all(x['paths']=='0' and x['worst_setup']=='none' for x in paths)
    public=t['public_sources']|spi['public_sources']|{n:sha(ROOT/n) for n in [
        'tools/nes_snapshot175.py','tools/check_nes_ready175.py','tools/nes_ready175_paths.tcl',
        'tools/check_nes_check165.py','tools/check_nes_retire165.py','tools/check_nes_retire165_nominal.py','tools/nes_secondary165_timing.tcl']}
    for n,h in public.items():assert sha(ROOT/n)==h,n
    r=dict(functional_passed=True,sources=m['sources'],baseline_sources=base,changed=changed,
        loader=t,spi=spi,fit=inspect(a.candidate),nominal=nominal(a.candidate),target_paths=paths,
        hardware_package=False,physical=False,extra_command_cycles=0,public_sources=public,
        scope='Reachable loader equivalence after reset; seeded one-step and single-byte/reset sequences, connected SPI with seeded READY/count. A5 output-only wires reuse prior review. No new game or hardware proof.')
    a.out.write_text(json.dumps(r,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(functional=True,timing=r['nominal']['passed'],worst=r['nominal']['worst_setup'],le=r['fit']['fit_le'],labs=r['fit']['used_labs'])))
if __name__=='__main__':main()
