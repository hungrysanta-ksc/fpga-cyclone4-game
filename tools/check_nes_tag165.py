# SPDX-License-Identifier: MIT
"""Bind request-tag tests, reproduced sources, and all-clock routed timing."""
from pathlib import Path
import argparse,csv,json
from nes_game147 import ROOT,sha
from nes_tag165 import transform
from check_nes_check165 import inspect
from check_nes_retire165 import nominal

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','candidate','reproduced','test']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();m=json.loads((a.candidate/'preparation.json').read_bytes())
    assert m==json.loads((a.reproduced/'preparation.json').read_bytes())
    assert len(m['sources'])==61 and m['changed']==['nes_rom_spi.sv']
    for n,h in m['sources'].items():
        assert sha(a.candidate/n)==sha(a.reproduced/n)==h,n
        assert sha(a.baseline/n)==m['baseline'][n],n
        if n!='nes_rom_spi.sv':assert h==m['baseline'][n],n
    assert (a.candidate/'nes_rom_spi.sv').read_text()==transform((a.baseline/'nes_rom_spi.sv').read_text())
    t=json.loads((a.test/'result.json').read_bytes())
    assert t['passed'] and t['conditional_states']==1409024 and t['captures']==393216
    assert t['wrong_capture_rejected'] and t['missing_compare_bit_rejected']
    assert 'reads=100 acks=7 corruptions=19 cancels=72 overlaps=2' in t['sequential_summary']
    assert sha(a.candidate/'nes_rom_spi.sv')==sha(a.test/'candidate.sv')==t['source_sha256']
    assert sha(a.baseline/'nes_rom_spi.sv')==t['reference_sha256']
    assert (a.test/'reference.sv').read_text()==(a.baseline/'nes_rom_spi.sv').read_text().replace('module nes_rom_spi_check(','module baseline_check165(',1)
    for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:assert sha(a.test/n)==m['sources'][n]
    for v in [m,t]:
        for n,h in v['public_sources'].items():assert sha(ROOT/n)==h,n
    for name,public in [('secondary165-timing.tcl','nes_secondary165_timing.tcl'),('predecode165-paths.tcl','nes_predecode165_paths.tcl')]:
        assert sha(a.candidate/name)==sha(ROOT/'tools'/public)
    rows=list(csv.DictReader((a.candidate/'predecode165-paths.tsv').open(),delimiter='\t'));assert len(rows)==9
    tags=list(csv.DictReader((a.candidate/'tag165-paths.tsv').open(),delimiter='\t'));assert len(tags)==6
    assert sha(a.candidate/'tag165-paths.tcl')==sha(ROOT/'tools/nes_tag165_paths.tcl')
    public={**m['public_sources'],**t['public_sources']}
    for n in ['check_nes_tag165.py','check_nes_check165.py','check_nes_oam_port165.py','check_nes_retire165.py','check_nes_retire165_nominal.py','nes_secondary165_timing.tcl','nes_predecode165_paths.tcl','nes_tag165_paths.tcl']:
        public['tools/'+n]=sha(ROOT/'tools'/n)
    v={**inspect(a.candidate),'nominal':nominal(a.candidate),'baseline_nominal':nominal(a.baseline),
       'targeted_nominal_setup_ns':{g:min(float(r['slack']) for r in rows if r['group']==g) for g in ['counter','capture','address']},
       'request_tag_nominal_setup_ns':{g:min(float(r['slack']) for r in tags if r['group']==g) for g in ['capture','response']},
       'conditional_states':t['conditional_states'],'capture_cases':t['captures'],'sequential_summary':t['sequential_summary'],
       'wrong_capture_rejected':True,'missing_compare_bit_rejected':True,'unchanged_files':60,
       'source_byte_reproduction':True,'response_edge_changed':False,'implementation_sdc_unchanged':True,
       'scope':'Request-tag invariant and conditional step equivalence; actual SPI/boot/READ16 with seeded READY/count and idle address boundaries. No game boot, full writes, full-board IO/CDC approval or new SD package.',
       'cartridge_sram_reserved':True,'whole_firmware_link':False,'hardware_package':False,'public_sources':public}
    assert not (a.candidate/'result.json').exists()
    (a.candidate/'result.json').write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({k:v[k] for k in ['fit_le','used_labs','nominal','targeted_nominal_setup_ns']}))
if __name__=='__main__':main()
