# SPDX-License-Identifier: MIT
"""Check exact input reproduction, OAM equivalence evidence, and real fit failure."""
from pathlib import Path
import argparse,json,re
from nes_game147 import ROOT,sha
from nes_oam_port165 import transform

def metrics(d,require_area=True):
    report=(d/'output_files/board.map.rpt').read_text(errors='replace')
    assert 'Analysis & Synthesis was successful' in (d/'map.log').read_text(errors='replace')
    assert re.search(r'; Optimization Technique\s*; '+('Area' if require_area else 'Balanced')+r'\s*;',report)
    def value(label):
        m=re.search(r'^; '+re.escape(label)+r'\s*; ([\d,]+)',report,re.M);assert m,label
        return int(m[1].replace(',',''))
    return {n:value(label) for n,label in [('estimated_le','Estimated Total logic elements'),('combinational','Total combinational functions'),('registers','Total registers'),('memory_bits','Total memory bits'),('pins','Total pins'),('virtual_pins','Total virtual pins')]}

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','area','candidate','reproduced','test','range-test','shared','physical','packed','data-enable']:
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();m=json.loads((a.candidate/'preparation.json').read_bytes());rep=json.loads((a.reproduced/'preparation.json').read_bytes())
    assert m['sources']==rep['sources'] and m['baseline']==rep['baseline']
    for n,h in m['sources'].items():
        assert sha(a.candidate/n)==sha(a.reproduced/n)==h,n
        assert sha(a.baseline/n)==m['baseline'][n],n
        if n not in ['rtl/ppu.sv','board.qsf']:assert h==m['baseline'][n],n
    assert (a.candidate/'rtl/ppu.sv').read_text()==transform((a.baseline/'rtl/ppu.sv').read_text())
    # Complete finite-domain arithmetic proof under the existing row<8 guard.
    for row in range(8):
        for lane in range(4):assert ((row*4+lane+32)&63)==(32|((row&7)<<2)|lane)
    t=json.loads((a.test/'result.json').read_bytes());r=json.loads((a.range_test/'result.json').read_bytes())
    for result in [t,r]:
        assert result['passed'] and result['source_sha256']==sha(a.candidate/'rtl/ppu.sv')
        assert result['reference_sha256']==sha(a.baseline/'rtl/ppu.sv')
    assert r['accepted_rows']==r['rejected_rows']==8 and r['wrong_bank_rejected']
    # Driver updates after execution changed only optional preparation modes.
    # Verify the executed module bytes directly, not a stale generator version.
    body=re.search(r'(?ms)^module OAMEval\(.*?^endmodule',(a.candidate/'rtl/ppu.sv').read_text())[0]
    for d in [a.test,a.range_test/'positive']:
        assert body.replace('module OAMEval(','module oam_banked(',1) in (d/'oam_banked.sv').read_text()
    for n,h in rep['public_sources'].items():assert sha(ROOT/n)==h,n
    fit=(a.candidate/'fit.log').read_text(errors='replace')
    assert 'Fitter requires 964 LABs' in fit and 'device contains only 963 LABs' in fit
    assert 'Error (170012)' in fit and 'Error (171000)' in fit
    fitreport=(a.candidate/'output_files/board.fit.rpt').read_text(errors='replace')
    assert re.search(r'Total logic elements\s*; 14,983 / 15,408',fitreport)
    assert re.search(r'M9Ks\s*; 35 / 56',fitreport)
    variants={}
    for name,d in [('shared-read',a.shared),('physical-area',a.physical),('packed-area',a.packed),('bank-data-enable',a.data_enable)]:
        v=dict(resources=metrics(d),adopted=False)
        if name!='shared-read':
            log=(d/'fit.log').read_text(errors='replace')
            v['errors']=re.findall(r'^Error \(\d+\):.*',log,re.M);assert v['errors']
        if name in ['physical-area','packed-area']:
            assert sha(d/'rtl/ppu.sv')==sha(a.candidate/'rtl/ppu.sv')
            assert sha(d/'output_files/board.map.rpt')==sha(a.candidate/'output_files/board.map.rpt')
            rr=(d/'output_files/board.fit.rpt').read_text(errors='replace')
            setting='Combinational Logic for Fitting' if name=='physical-area' else 'Auto Packed Registers'
            value='On' if name=='physical-area' else 'Minimize Area'
            assert re.search(re.escape(setting)+r'\s*; '+value+r'\s*;',rr)
        variants[name]=v
    result=dict(synthesis_pass=True,fit_pass=False,selected='map02/reproduce',resources=metrics(a.candidate),
        baseline_area_resources=metrics(a.area),board_resources=metrics(a.baseline,False),
        combinational_reduction=metrics(a.area)['combinational']-metrics(a.candidate)['combinational'],
        oam_combinational_before=5663,oam_combinational_after=3939,
        failed_fit_le=14983,required_labs=964,available_labs=963,m9k_blocks=35,
        rtl_changed=True,clock_latency_changed=False,source_byte_reproduction=True,unchanged_files=len(m['sources'])-2,
        finite_guard_domain_cases=32,edge_test={k:t[k] for k in ['cycles','row_copies','cpu_writes','savestate_writes','write_collisions']},
        range_test={k:r[k] for k in ['accepted_rows','rejected_rows','compared_bytes','wrong_bank_rejected']},rejected_variants=variants,
        cartridge_sram_reserved=True,timing_approved=False,whole_firmware_link=False,hardware_package=False,
        functional_scope='Actual banked OAM every-edge comparison plus all 16 extra-row values and wrong-bank negative. No new game boot; no latency/CE/write-priority change. Not a full formal proof.',
        public_sources={n:sha(ROOT/n) for n in ['tools/nes_oam_port165.py','tools/test_nes_oam_range165.py','tools/check_nes_oam_port165.py','tests/nes-functional/oam_range165_tb.sv','tools/test_nes_oam_select165.py','tests/nes-functional/oam_banked_tb.sv']})
    assert result['combinational_reduction']==1719
    assert not (a.candidate/'result.json').exists(),'Do not overwrite completed evidence'
    (a.candidate/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
