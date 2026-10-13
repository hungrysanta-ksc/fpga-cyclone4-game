# SPDX-License-Identifier: MIT
"""Exhaust all guarded extra-row values, then require a wrong-bank control to fail."""
from pathlib import Path
import argparse, json, os, re, shutil, subprocess
from nes_game147 import ROOT, sha
from nes_oam_port165 import transform

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
    assert changed==transform(original,'secondary-range')
    for case in ['positive','wrong-bank']:
        d=a.out/case;d.mkdir()
        for body,name in [(original,'oam_reference'),(changed,'oam_banked')]:
            if case=='wrong-bank' and name=='oam_banked':
                needle="{1'b1, oam_secondary_row_ex[2:0], 2'b"
                assert body.count(needle)==4
                body=body.replace(needle,"{1'b0, oam_secondary_row_ex[2:0], 2'b")
            m=re.search(r'(?ms)^module OAMEval\(.*?^endmodule',body);assert m
            (d/(name+'.sv')).write_text(body[:body.index('import regs_savestates::*;')]+'import regs_savestates::*;\n'+m[0].replace('module OAMEval(', 'module '+name+'(',1)+'\n')
        for n in ['regs_savestates.sv','bus_savestates.vhd']:
            shutil.copy2(a.prepared/'rtl'/n,d/n)
        shutil.copy2(ROOT/'tests/nes-functional/oam_range165_tb.sv',d/'oam_range165_tb.sv')
        def run(exe,args,label,negative=False):
            with (d/(label+'.log')).open('wb') as f:
                r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=120)
            log=(d/(label+'.log')).read_text(errors='replace')
            if negative:
                assert '** Fatal: range mismatch row=0 byte=0' in log,log[-3000:]
                assert 'PASS OAM RANGE' not in log
            else:
                assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),log[-3000:]
            return log
        run('vlib',['work'],'vlib')
        run('vcom',['-2008','bus_savestates.vhd'],'vcom')
        run('vlog',['-sv','-mfcu','regs_savestates.sv','oam_reference.sv','oam_banked.sv','oam_range165_tb.sv'],'vlog')
        log=run('vsim',['-c','oam_range165_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation',case=='wrong-bank')
        if case=='positive':assert 'PASS OAM RANGE accepted=8 rejected=8 bytes=1024' in log
    result=dict(passed=True,accepted_rows=8,rejected_rows=8,compared_bytes=1024,wrong_bank_rejected=True,
        source_sha256=sha(a.prepared/'rtl/ppu.sv'),reference_sha256=sha(a.baseline/'rtl/ppu.sv'),
        public_sources={n:sha(ROOT/n) for n in ['tools/nes_oam_port165.py','tools/test_nes_oam_range165.py','tests/nes-functional/oam_range165_tb.sv']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()
