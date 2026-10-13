# SPDX-License-Identifier: MIT
"""Check invalid storage masking, extra writes, and a wrong-validity negative."""
from pathlib import Path
import argparse, json, os, re, shutil, subprocess
from nes_game147 import ROOT, sha
from nes_oam_port165 import transform as range_transform
from nes_oam_secondary165 import transform

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','prepared','out','questa-bin']:
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    assert not a.out.exists() and str(a.out).isascii()
    a.out.mkdir(parents=True)
    original=(a.baseline/'rtl/ppu.sv').read_text()
    changed=(a.prepared/'rtl/ppu.sv').read_text()
    assert changed==transform(range_transform(original),'valid-mask')
    for case in ['positive','wrong-valid']:
        d=a.out/case;d.mkdir()
        for body,name in [(original,'oam_reference'),(changed,'oam_banked')]:
            if case=='wrong-valid' and name=='oam_banked':
                needle='else if(extra_byte)temp_valid[32+temp_index]<=1;'
                assert body.count(needle)==1
                body=body.replace(needle,'else if(extra_byte)temp_valid[32+temp_index]<=0;')
            m=re.search(r'(?ms)^module OAMEval\(.*?^endmodule',body);assert m
            (d/(name+'.sv')).write_text(body[:body.index('import regs_savestates::*;')]+'import regs_savestates::*;\n'+m[0].replace('module OAMEval(', 'module '+name+'(',1)+'\n')
        for n in ['regs_savestates.sv','bus_savestates.vhd']:
            shutil.copy2(a.prepared/'rtl'/n,d/n)
        bench=(ROOT/'tests/nes-functional/oam_range165_tb.sv').read_text()
        needle='reset=0;ce=1;rendering_enabled=1;'
        assert bench.count(needle)==1
        bench=bench.replace(needle,"for(integer stale=0;stale<64;stale++)candidate.temp_storage[stale]=8'h37;\n  "+needle)
        (d/'oam_range165_tb.sv').write_text(bench)
        def run(exe,args,label,negative=False):
            with (d/(label+'.log')).open('wb') as f:
                r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=120)
            log=(d/(label+'.log')).read_text(errors='replace')
            if negative:
                assert '** Fatal: range mismatch row=0 byte=32' in log,log[-3000:]
                assert 'PASS OAM RANGE' not in log
            else:
                assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),log[-3000:]
            return log
        run('vlib',['work'],'vlib')
        run('vcom',['-2008','bus_savestates.vhd'],'vcom')
        run('vlog',['-sv','-mfcu','regs_savestates.sv','oam_reference.sv','oam_banked.sv','oam_range165_tb.sv'],'vlog')
        log=run('vsim',['-c','oam_range165_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation',case=='wrong-valid')
        if case=='positive':assert 'PASS OAM RANGE accepted=8 rejected=8 bytes=1024' in log
    result=dict(passed=True,accepted_rows=8,rejected_rows=8,compared_bytes=1024,wrong_valid_rejected=True,stale_storage_injected=True,
        source_sha256=sha(a.prepared/'rtl/ppu.sv'),reference_sha256=sha(a.baseline/'rtl/ppu.sv'),
        public_sources={n:sha(ROOT/n) for n in ['tools/nes_oam_port165.py','tools/nes_oam_secondary165.py','tools/test_nes_oam_secondary165.py','tests/nes-functional/oam_range165_tb.sv']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()
