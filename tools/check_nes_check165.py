# SPDX-License-Identifier: MIT
"""Exact input/evidence reuse checks, full fitted resources and unchanged-SDC STA."""
from pathlib import Path
import argparse,csv,json,re
from nes_game147 import ROOT,sha
from nes_check165 import transform
from check_nes_oam_port165 import metrics

def inspect(d):
    fit=(d/'output_files/board.fit.rpt').read_text(errors='replace')
    assert 'Fitter was successful' in (d/'fit.log').read_text(errors='replace')
    def value(label):
        m=re.search(re.escape(label)+r'\s*; ([\d,]+)',fit);assert m,label
        return int(m[1].replace(',',''))
    rows=list(csv.DictReader((d/'secondary165-clocks.tsv').open(),delimiter='\t'))
    clocks=sorted({r['clock'] for r in rows});corners=sorted({r['corner'] for r in rows})
    assert len(clocks)==4 and len(corners)==3
    minima={c:{k:min(float(r['slack']) for r in rows if r['clock']==c and r['kind']==k) for k in ['setup','hold']} for c in clocks}
    worst=min((r for r in rows if r['kind']=='setup'),key=lambda r:float(r['slack']))
    mixed=[float(x) for f in d.glob('secondary165-*-mixed-setup.rpt') for x in re.findall(r'Path #\d+: Setup slack is (-?[\d.]+)',f.read_text())]
    assert len(mixed)==30
    ucp=(d/'secondary165-unconstrained.rpt').read_text()
    io={n:int(re.search(re.escape(n)+r'\s*; (\d+)',ucp)[1]) for n in ['Unconstrained Clocks','Unconstrained Input Ports','Unconstrained Output Ports']}
    return dict(synthesis_pass=True,fit_pass=True,resources=metrics(d),fit_le=value('Total logic elements'),used_labs=value('Total LABs:  partially or completely used'),m9k_blocks=value('M9Ks'),
        same_clock_pass=all(v[k]>=0 for v in minima.values() for k in ['setup','hold']),
        timing=dict(rows=len(rows),corners=corners,minima_ns=minima,worst_setup=worst,raw_mixed_setup_min_ns=min(mixed),unconstrained=io),timing_approved=False)

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','candidate','reproduced','prefix','data-mux','test','path-test']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();m=json.loads((a.candidate/'preparation.json').read_bytes());rep=json.loads((a.reproduced/'preparation.json').read_bytes())
    assert m==rep
    for n,h in m['sources'].items():
        assert sha(a.candidate/n)==sha(a.reproduced/n)==h,n
        assert sha(a.baseline/n)==m['baseline'][n],n
        if n!='nes_rom_spi.sv':assert h==m['baseline'][n],n
    before=(a.baseline/'nes_rom_spi.sv').read_text();after=(a.candidate/'nes_rom_spi.sv').read_text()
    assert after==transform(before,m['variant'])
    attribute='(* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF" *) '
    assert after.count(attribute+'output reg [7:0] load_data,')==1
    normalized=after.replace(attribute+'output reg [7:0] load_data,','output reg [7:0] load_data,')
    normalized=normalized.replace('AUTO_CLOCK_ENABLE_RECOGNITION OFF; -name ALLOW_SYNCH_CTRL_USAGE OFF" *) reg [18:0] check_next;', 'AUTO_CLOCK_ENABLE_RECOGNITION OFF" *) reg [18:0] check_next;')
    assert normalized==transform(before,'prefix-only')==(a.test/'candidate.sv').read_text()
    assert normalized==(a.path_test/'inputs/nes_rom_spi.sv').read_text()
    t=json.loads((a.test/'result.json').read_bytes());s=json.loads((a.path_test/'result.json').read_bytes())
    assert t['passed'] and t['states']==786432 and t['wrong_carry_rejected']
    assert t['reference_sha256']==sha(a.baseline/'nes_rom_spi.sv') and t['source_sha256']==sha(a.test/'candidate.sv')
    assert s['passed'] and s['expected_reply_id']=='6B' and s['sources']['nes_rom_spi.sv']==t['source_sha256']
    for n,h in s['sources'].items():
        assert sha(a.path_test/'path'/n)==h,n
        if n!='game147_path_tb.sv':assert sha(a.path_test/'inputs'/n)==h,n
    for d in [a.candidate,a.prefix,a.data_mux]:
        assert sha(d/'secondary165-timing.tcl')==sha(ROOT/'tools/nes_secondary165_timing.tcl')
        assert sha(d/'board.sdc')==sha(a.baseline/'board.sdc')
    assert sha(a.candidate/'check165-paths.tcl')==sha(ROOT/'tools/nes_check165_paths.tcl')
    targeted=list(csv.DictReader((a.candidate/'check165-paths.tsv').open(),delimiter='\t'))
    assert len(targeted)==9
    groups={g:min(float(r['slack']) for r in targeted if r['group']==g) for g in ['check','loader','miso']}
    public={n:sha(ROOT/n) for n in ['tools/nes_check165.py','tools/test_nes_check165.py','tools/test_nes_check_path165.py','tools/check_nes_check165.py','tools/nes_check165_paths.tcl','tools/nes_secondary165_timing.tcl','tools/test_nes_game149_spi.py','tests/nes-functional/game147_path_tb.sv']}
    result={**inspect(a.candidate), 'selected':a.candidate.name,'prefix_candidate':inspect(a.prefix),'data_mux_candidate':inspect(a.data_mux),
        'targeted_setup_ns':groups,'functional_states':786432,'all_counter_values':524288,'priority_states':262144,'wrong_carry_rejected':True,
        'spi_summary':s['summary'],'reuse_normalization':'Remove only load_data AUTO_CLOCK_ENABLE_RECOGNITION OFF and check_next ALLOW_SYNCH_CTRL_USAGE OFF attributes; executed RTL otherwise byte-identical.',
        'unchanged_files':len(m['sources'])-1,'clock_latency_changed':False,'source_byte_reproduction':True,
        'cartridge_sram_reserved':True,'whole_firmware_link':False,'hardware_package':False,'public_sources':public}
    (a.candidate/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
