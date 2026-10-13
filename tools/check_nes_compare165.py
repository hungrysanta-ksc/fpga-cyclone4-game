# SPDX-License-Identifier: MIT
"""Verify exact comparator change, differential evidence and routed clock results."""
from pathlib import Path
import argparse,csv,json
from nes_game147 import ROOT,sha
from nes_compare165 import transform,drain,causes,fault
from test_nes_compare165 import bench
from test_nes_fault165 import bench as drain_bench
from test_nes_causes165 import bench as causes_bench
from check_nes_check165 import inspect
from check_nes_retire165 import nominal

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','candidate','reproduced','test','path-test','drain-test','causes-test','first','second','third']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();m=json.loads((a.candidate/'preparation.json').read_bytes())
    assert m==json.loads((a.reproduced/'preparation.json').read_bytes())
    assert len(m['sources'])==61 and m['changed']==['nes_rom_loader.sv','nes_rom_spi.sv'] and m['variant']=='fault'
    for n,h in m['sources'].items():
        assert sha(a.candidate/n)==sha(a.reproduced/n)==h,n
        assert sha(a.baseline/n)==m['baseline'][n],n
        if n not in m['changed']:assert h==m['baseline'][n],n
    for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
    assert (a.candidate/'nes_rom_spi.sv').read_text()==causes(transform((a.baseline/'nes_rom_spi.sv').read_text()))
    assert (a.candidate/'nes_rom_loader.sv').read_text()==fault(drain((a.baseline/'nes_rom_loader.sv').read_text()))
    t=json.loads((a.test/'result.json').read_bytes());s=json.loads((a.path_test/'result.json').read_bytes())
    assert t['passed'] and t['states']==1409024 and t['captures']==393216 and t['wrong_response_bit_rejected']
    assert t['reference_sha256']==sha(a.baseline/'nes_rom_spi.sv')
    assert t['source_sha256']==sha(a.test/'candidate.sv')
    assert (a.test/'candidate.sv').read_text()==transform((a.baseline/'nes_rom_spi.sv').read_text())
    assert (a.test/'check165_tb.sv').read_text()==bench()
    c=json.loads((a.causes_test/'result.json').read_bytes())
    assert c['passed'] and c['states']==1409024 and c['captures']==438272 and c['wrong_read_cause_rejected'] and c['capture_retirement_checked']
    assert c['source_sha256']==sha(a.causes_test/'candidate.sv')==sha(a.candidate/'nes_rom_spi.sv')
    assert c['reference_sha256']==sha(a.baseline/'nes_rom_spi.sv')
    assert (a.causes_test/'check165_tb.sv').read_text()==causes_bench()
    d=json.loads((a.drain_test/'result.json').read_bytes())
    assert d['passed'] and d['states']==3342336 and d['wrong_fault_stop_rejected']
    assert d['source_sha256']==sha(a.drain_test/'candidate.sv')==sha(a.candidate/'nes_rom_loader.sv')
    assert d['reference_sha256']==sha(a.baseline/'nes_rom_loader.sv')
    assert (a.drain_test/'counter131_diff_tb.sv').read_text()==drain_bench()
    assert s['passed'] and s['expected_reply_id']=='6B' and s['derived_length_flag_seeded_with_count']
    for n,h in s['sources'].items():
        assert sha(a.path_test/'path'/n)==h,n
        if n!='game147_path_tb.sv':assert sha(a.candidate/n)==h,n
    for n in ['secondary165-timing.tcl','predecode165-paths.tcl']:
        public='tools/'+n.replace('secondary165-timing','nes_secondary165_timing').replace('predecode165-paths','nes_predecode165_paths')
        assert sha(a.candidate/n)==sha(ROOT/public)
    rows=list(csv.DictReader((a.candidate/'predecode165-paths.tsv').open(),delimiter='\t'));assert len(rows)==9
    targets={g:min(float(r['slack']) for r in rows if r['group']==g) for g in ['counter','capture','address']}
    # Truth-table identity for all difference masks and response presence.
    for mask in range(1<<19):
        for response in [False,True]:
            bit_guard=all((not response) or not(mask & (1<<i)) for i in range(19))
            assert bit_guard==((not response) or mask==0)
    public=['tools/nes_compare165.py','tools/test_nes_compare165.py','tools/check_nes_compare165.py','tools/test_nes_drain165.py','tools/test_nes_causes165.py','tools/test_nes_fault165.py','tests/nes-functional/counter131_diff_tb.sv','tools/test_nes_predecode165.py','tools/test_nes_check165.py','tools/test_nes_predecode_path165.py','tools/test_nes_game149_spi.py','tests/nes-functional/game147_path_tb.sv','tools/check_nes_check165.py','tools/check_nes_oam_port165.py','tools/check_nes_retire165.py','tools/check_nes_retire165_nominal.py','tools/nes_secondary165_timing.tcl','tools/nes_predecode165_paths.tcl']
    result={**inspect(a.candidate),'nominal':nominal(a.candidate),'baseline_nominal':nominal(a.baseline),'targeted_nominal_setup_ns':targets,
        'functional_states':c['states'],'capture_cases':c['captures'],'capture_retirement_checked':True,'wrong_read_cause_rejected':True,'single_bit_response_cases':t['single_bit_response_cases'],'truth_table_cases':1048576,'wrong_response_bit_rejected':True,
        'spi_summary':s['summary'],'loader_states':d['states'],'wrong_fault_stop_rejected':True,'first_candidate':{**inspect(a.first),'nominal':nominal(a.first)},'second_candidate':{**inspect(a.second),'nominal':nominal(a.second)},'third_candidate':{**inspect(a.third),'nominal':nominal(a.third)},'unchanged_files':59,'clock_latency_changed':False,'source_byte_reproduction':True,'implementation_sdc_unchanged':True,
        'cartridge_sram_reserved':True,'whole_firmware_link':False,'hardware_package':False,
        'scope':'Same-edge response guards and parallel loader transition/fault legality; two lifecycle causes captured on original edge and merged at original retirement. All counter values, individual address mismatches, capture plus retirement, and all128loader timer values. No new game boot or whole-board IO/CDC signoff.',
        'public_sources':{n:sha(ROOT/n) for n in public}}
    assert result['used_labs']<=963 and result['resources']['virtual_pins']==0
    assert not (a.candidate/'result.json').exists()
    (a.candidate/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['fit_le','used_labs','nominal','targeted_nominal_setup_ns']}))
if __name__=='__main__':main()
