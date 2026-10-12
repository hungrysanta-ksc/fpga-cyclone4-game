# SPDX-License-Identifier: MIT
"""Verify local synthesis settings with unchanged RTL and separate nominal STA."""
from pathlib import Path
import argparse,csv,json
from nes_game147 import ROOT,sha
from nes_speed165 import ASSIGNMENTS
from check_nes_check165 import inspect
from check_nes_retire165 import nominal

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','candidate','reproduced']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();m=json.loads((a.candidate/'preparation.json').read_bytes())
    assert m==json.loads((a.reproduced/'preparation.json').read_bytes())
    assert len(m['sources'])==61 and m['changed']==['board.qsf']
    for n,h in m['sources'].items():
        assert sha(a.candidate/n)==sha(a.reproduced/n)==h,n
        assert sha(a.baseline/n)==m['baseline'][n],n
        if n!='board.qsf':assert h==m['baseline'][n],n
    assert (a.candidate/'board.qsf').read_text()==(a.baseline/'board.qsf').read_text()+ASSIGNMENTS
    for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
    log=(a.candidate/'map.log').read_text(errors='replace')
    assert 'Ignored assignment' not in log and 'Critical Warning' not in log
    report=(a.candidate/'output_files/board.map.rpt').read_text(errors='replace')
    assert '; Area ' in report
    for target in ['nes_rom_spi_check:control','nes_rom_loader:loader']:assert target in report
    applied=(a.candidate/'speed-assignments.txt').read_text()
    assert applied.splitlines()==['core|loader_boot|control=SPEED','core|loader_boot|boot|loader=SPEED']
    pub=json.loads((ROOT/'analysis/predecode165-verification.json').read_bytes())
    assert sha(a.baseline/'result.json')==pub['raw_result_sha256']['map03']
    for n,h in pub['public_sources'].items():assert sha(ROOT/n)==h,n
    rows=list(csv.DictReader((a.candidate/'predecode165-paths.tsv').open(),delimiter='\t'));assert len(rows)==9
    public=['tools/nes_speed165.py','tools/check_nes_speed165.py','tools/check_nes_check165.py','tools/check_nes_oam_port165.py','tools/check_nes_retire165.py','tools/check_nes_retire165_nominal.py','tools/nes_secondary165_timing.tcl','tools/nes_predecode165_paths.tcl']
    v={**inspect(a.candidate),'nominal':nominal(a.candidate),'baseline_nominal':nominal(a.baseline),
       'targeted_nominal_setup_ns':{g:min(float(r['slack']) for r in rows if r['group']==g) for g in ['counter','capture','address']},
       'unchanged_files':60,'source_byte_reproduction':True,'clock_latency_changed':False,'implementation_sdc_unchanged':True,
       'functional_reuse':'All RTL byte-identical to selected predecode165 map03; reuse its executed boundary/SPI/loader results. This trial changes only two synthesis instance settings.',
       'reuse_verification_sha256':sha(ROOT/'analysis/predecode165-verification.json'),
       'instance_settings_readback':applied.splitlines(),'ignored_assignments':False,'cartridge_sram_reserved':True,'whole_firmware_link':False,'hardware_package':False,
       'public_sources':{n:sha(ROOT/n) for n in public}}
    assert not (a.candidate/'result.json').exists()
    (a.candidate/'result.json').write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({k:v[k] for k in ['fit_le','used_labs','nominal','targeted_nominal_setup_ns']}))
if __name__=='__main__':main()
