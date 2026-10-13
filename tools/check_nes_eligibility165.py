# SPDX-License-Identifier: MIT
"""Bind direct READY eligibility, connected equivalence, and routed STA."""
from pathlib import Path
import argparse,csv,json
from nes_game147 import ROOT,sha
from nes_eligibility165 import loader,boot,physical,TAG_OLD,TAG_NEW
from test_nes_eligibility165 import unit,connected
from test_nes_reader_last165 import bench
from check_nes_check165 import inspect
from check_nes_retire165 import nominal

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','tag','tag-test','candidate','reproduced','test','reader-test','first']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();m=json.loads((a.candidate/'preparation.json').read_bytes())
    assert m==json.loads((a.reproduced/'preparation.json').read_bytes())
    assert len(m['sources'])==61 and m['changed']==['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','nes_rom_spi.sv']
    for n,h in m['sources'].items():
        assert sha(a.candidate/n)==sha(a.reproduced/n)==h,n
        assert sha(a.baseline/n)==m['baseline'][n],n
        if n not in m['changed']:assert h==m['baseline'][n],n
    assert (a.candidate/'nes_rom_loader.sv').read_text()==loader((a.baseline/'nes_rom_loader.sv').read_text())
    assert (a.candidate/'nes_rom_boot.sv').read_text()==boot((a.baseline/'nes_rom_boot.sv').read_text())
    assert (a.candidate/'nes_rom_physical.sv').read_text()==physical((a.baseline/'nes_rom_physical.sv').read_text())
    assert (a.candidate/'nes_rom_spi.sv').read_text()==(a.tag/'nes_rom_spi.sv').read_text().replace(TAG_OLD,TAG_NEW)
    assert sha(a.tag/'result.json')==m['tag_reference_sha256']
    t=json.loads((a.test/'result.json').read_bytes());assert t['passed'] and t['eligibility_combinations']==1024 and t['missing_fault_rejected'] and t['loader_fault_cases']==26
    for n,h in t['sources'].items():assert sha(a.test/n)==sha(a.candidate/n)==h,n
    assert (a.test/'eligibility165_tb.sv').read_text()==unit()
    assert (a.test/'tag165_tb.sv').read_text()==connected()
    assert sha(a.tag_test/'result.json')==t['spi_reuse_result_sha256']
    r=json.loads((a.reader_test/'result.json').read_bytes())
    assert r['passed'] and r['cases']==5 and r['reads']==120 and r['cancels']==126 and r['stopped_resets']==5 and r['wrong_terminal_rejected']
    assert sha(a.candidate/'nes_rom_physical.sv')==r['source_sha256'] and sha(a.baseline/'nes_rom_physical.sv')==r['reference_sha256']
    assert (a.reader_test/'reader_last165_tb.sv').read_text()==bench()
    first=json.loads((a.first/'result.json').read_bytes())
    assert first['source_byte_reproduction'] and first['nominal']['worst_setup']['slack']=='-0.856'
    for v in [m,t,r]:
        for n,h in v['public_sources'].items():assert sha(ROOT/n)==h,n
    tables={}
    for stem,script in [('predecode165','nes_predecode165_paths.tcl'),('tag165','nes_tag165_paths.tcl'),('eligibility165','nes_eligibility165_paths.tcl'),('reader-last165','nes_reader_last165_paths.tcl')]:
        assert sha(a.candidate/(stem+'-paths.tcl'))==sha(ROOT/'tools'/script)
        tables[stem]=list(csv.DictReader((a.candidate/(stem+'-paths.tsv')).open(),delimiter='\t'))
    assert [len(tables[n]) for n in ['predecode165','tag165','eligibility165','reader-last165']]==[9,6,3,6]
    public={**m['public_sources'],**t['public_sources'],**r['public_sources']}
    for n in ['check_nes_eligibility165.py','check_nes_check165.py','check_nes_oam_port165.py','check_nes_retire165.py','check_nes_retire165_nominal.py','nes_secondary165_timing.tcl','nes_predecode165_paths.tcl','nes_tag165_paths.tcl','nes_eligibility165_paths.tcl','nes_reader_last165_paths.tcl']:
        public['tools/'+n]=sha(ROOT/'tools'/n)
    v={**inspect(a.candidate),'nominal':nominal(a.candidate),'baseline_nominal':nominal(a.baseline),'tag_nominal':nominal(a.tag),
       'targeted_nominal_setup_ns':{g:min(float(r['slack']) for r in tables['predecode165'] if r['group']==g) for g in ['counter','capture','address']},
       'request_tag_nominal_setup_ns':{g:min(float(r['slack']) for r in tables['tag165'] if r['group']==g) for g in ['capture','response']},
       'fault_cause_nominal_setup_ns':min(float(r['slack']) for r in tables['eligibility165']),
       'eligibility_combinations':1024,'loader_fault_cases':26,'sequential_summary':t['sequential_summary'],
       'spi_reuse_result_sha256':t['spi_reuse_result_sha256'],'spi_reuse_states':t['spi_reuse_states'],'spi_reuse_captures':t['spi_reuse_captures'],
       'reader_terminal_equivalence':r,'first_trial_result_sha256':sha(a.first/'result.json'),
       'reader_terminal_nominal_setup_ns':{g:min(float(row['slack']) for row in tables['reader-last165'] if row['group']==g) for g in ['terminal','sample']},
       'first_trial_nominal':first['nominal'],'first_trial_fault_cause_ns':first['fault_cause_nominal_setup_ns'],
       'source_byte_reproduction':True,'response_edge_changed':False,'implementation_sdc_unchanged':True,'unchanged_files':57,
       'scope':'Direct combinational READY eligibility and registered reader-terminal predicate. Actual SPI/boot/READ16 boundary equivalence with seeded loader READY/count; separate old-reader register/pin comparison for both owners, READ_CYCLES1/2/3/16 and two board-count phases. Prior SPI state/capture evidence reused only after exact one-comment normalization. No game boot, full writes, new SNES run, MCU loop or whole-board IO/CDC signoff.',
       'cartridge_sram_reserved':True,'whole_firmware_link':False,'hardware_package':False,'public_sources':public}
    assert not (a.candidate/'result.json').exists()
    (a.candidate/'result.json').write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({k:v[k] for k in ['fit_le','used_labs','nominal','targeted_nominal_setup_ns','fault_cause_nominal_setup_ns']}))
if __name__=='__main__':main()
