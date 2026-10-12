# SPDX-License-Identifier: MIT
"""Check secondary OAM reproduction, changed-boundary tests and routed timing.

Fitter success is deliberately separate from timing/hardware approval.
"""
from pathlib import Path
import argparse,csv,json,re
from nes_game147 import ROOT,sha
from check_nes_oam_port165 import metrics
from nes_oam_port165 import transform as range_transform
from nes_oam_secondary165 import transform


def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','candidate','reproduced','test','valid-test']:
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();d=a.candidate
    m=json.loads((d/'preparation.json').read_bytes())
    rep=json.loads((a.reproduced/'preparation.json').read_bytes())
    assert m['sources']==rep['sources'] and m['baseline']==rep['baseline']
    for n,h in m['sources'].items():
        assert sha(d/n)==sha(a.reproduced/n)==h,n
        assert sha(a.baseline/n)==m['baseline'][n],n
        if n not in ['rtl/ppu.sv','board.qsf']:assert h==m['baseline'][n],n
    assert (d/'rtl/ppu.sv').read_text()==transform(range_transform((a.baseline/'rtl/ppu.sv').read_text()))
    public=dict(rep['public_sources']);tests={}
    body=re.search(r'(?ms)^module OAMEval\(.*?^endmodule',(d/'rtl/ppu.sv').read_text())[0]
    for label,folder,rtl in [('edges',a.test,a.test/'oam_banked.sv'),('validity',a.valid_test,a.valid_test/'positive/oam_banked.sv')]:
        t=json.loads((folder/'result.json').read_bytes())
        assert t['passed'] and t['source_sha256']==sha(d/'rtl/ppu.sv')
        assert t['reference_sha256']==sha(a.baseline/'rtl/ppu.sv')
        assert body.replace('module OAMEval(','module oam_banked(',1) in rtl.read_text()
        public.update(t['public_sources']);tests[label]=t
    assert tests['edges']['cycles']==216362
    assert tests['validity']['accepted_rows']==tests['validity']['rejected_rows']==8
    assert tests['validity']['compared_bytes']==1024
    assert tests['validity']['wrong_valid_rejected'] and tests['validity']['stale_storage_injected']
    fit=(d/'output_files/board.fit.rpt').read_text(errors='replace')
    assert 'Fitter was successful' in (d/'fit.log').read_text(errors='replace')
    for pattern in [r'Fitter Status\s*; Successful',r'Total logic elements\s*; 15,052 / 15,408',r'Total LABs:.*?; 963 / 963',r'M9Ks\s*; 35 / 56']:
        assert re.search(pattern,fit),pattern
    assert sha(d/'secondary165-timing.tcl')==sha(ROOT/'tools/nes_secondary165_timing.tcl')
    rows=list(csv.DictReader((d/'secondary165-clocks.tsv').open(),delimiter='\t'))
    corners=sorted({r['corner'] for r in rows});clocks=sorted({r['clock'] for r in rows})
    assert len(corners)==3 and len(clocks)==4
    minima={c:{k:min(float(r['slack']) for r in rows if r['clock']==c and r['kind']==k) for k in ['setup','hold']} for c in clocks}
    worst=min((r for r in rows if r['kind']=='setup'),key=lambda r:float(r['slack']))
    assert float(worst['slack'])==-1.218 and worst['to'].endswith('control|check_next[7]')
    assert min(v['hold'] for v in minima.values())==0.155
    path=(d/'secondary165-0-3-setup.rpt').read_text()
    assert re.search(r'Max Delay Exception\s*; 5.500',path)
    ucp=(d/'secondary165-unconstrained.rpt').read_text()
    for label,value in [('Unconstrained Clocks',0),('Unconstrained Input Ports',54),('Unconstrained Output Ports',57)]:
        assert re.search(re.escape(label)+r'\s*; '+str(value)+r'\s*;',ucp)
    mixed=[float(x) for file in d.glob('secondary165-*-mixed-setup.rpt') for x in re.findall(r'Path #\d+: Setup slack is (-?[\d.]+)',file.read_text())]
    assert len(mixed)==30
    for n in ['tools/check_nes_oam_secondary165.py','tools/check_nes_oam_port165.py','tools/nes_secondary165_timing.tcl']:
        public[n]=sha(ROOT/n)
    for n,h in public.items():assert sha(ROOT/n)==h,n
    result=dict(synthesis_pass=True,fit_pass=True,timing_approved=False,selected='map03/reproduce',
        resources=metrics(d),fit_le=15052,used_labs=963,available_labs=963,m9k_blocks=35,
        source_byte_reproduction=True,unchanged_files=len(m['sources'])-2,rtl_changed=True,clock_latency_changed=False,
        tests=tests,timing=dict(corners=corners,rows=len(rows),minima_ns=minima,worst_setup=worst,
            setup_budget_ns=5.5,raw_mixed_setup_min_ns=min(mixed),unconstrained_input_ports=54,unconstrained_output_ports=57,
            nominal_only_reanalysis=False,cdc_and_io_approved=False),
        cartridge_sram_reserved=True,whole_firmware_link=False,hardware_package=False,public_sources=public)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ['fit_pass','timing_approved','resources','timing']}))


if __name__=='__main__':main()
