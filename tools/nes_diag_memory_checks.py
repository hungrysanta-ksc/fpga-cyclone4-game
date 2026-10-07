# SPDX-License-Identifier: MIT
"""067 actual RTL pin-delay cases, causal mutations and explicit evidence scope."""
from pathlib import Path
import argparse, json, os, re, shutil
from nes_diag_memory_timing import materialize
from nes_spi_boot import ROOT, run, sha, put
from nes_rom_geometry import replace


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--questa-bin',type=Path,required=True)
    a=p.parse_args()
    assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(__file__,out/'executed-driver.py')
    cases=[
        ('zero80',81920,0,0,0,0,8,None,None),
        ('address2',81920,2,0,0,2,8,None,None),
        ('slow96',98304,20,0,20,20,8,None,None),
        ('control20',81920,0,20,0,0,0,None,None),
        ('bad-write-setup',81920,2,0,0,0,8,'write-setup','ADDRESS_SETUP_AT_CE read=0'),
        ('bad-read-setup',81920,2,0,0,0,8,'read-setup','ADDRESS_SETUP_AT_CE read=1'),
        ('bad-read-hold',81920,0,0,0,0,0,'read-hold','READ_SAMPLE_HOLD'),
        ('outside126',81920,126,0,0,0,8,None,'ADDRESS_SETUP_AT_CE read=0'),
    ]
    results=[]
    for name,total,ad,cd,dd,dq,hz,mutation,expected in cases:
        c=out/name;c.mkdir();materialize(c)
        if mutation=='write-setup':
            f=c/'nes_rom_loader.sv';put(f,replace(f.read_text(),'remaining<=3;state<=SETUP;','remaining<=3;state<=WRITE;'))
        if mutation=='read-setup':
            f=c/'nes_rom_physical.sv';put(f,replace(f.read_text(),"remaining<=CW'(READ_CYCLES);state<=SETUP;","remaining<=CW'(READ_CYCLES);state<=ACTIVE;"))
        if mutation=='read-hold':
            f=c/'nes_rom_physical.sv';put(f,replace(f.read_text(),'(state==ACTIVE || state==HOLD)','(state==ACTIVE)'))
        tb=ROOT/'tests/nes-functional/diag_memory_timing_tb.sv'
        shutil.copy2(tb,c/tb.name)
        files=['nes_rom_loader.sv','nes_rom_physical.sv','nes_rom_boot.sv',tb.name]
        for tool,args in [('vlib',['work']),('vlog',['-sv',*files])]:
            log=run([a.questa_bin/(tool+'.exe'),*args],c,tool)
            assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
        try:
            log=run([a.questa_bin/'vsim.exe','-c','-t','1ps','diag_memory_timing_tb',
                     f'+TOTAL={total}',f'+AD={ad}',f'+CD={cd}',f'+DD={dd}',f'+DQ={dq}',f'+HZ={hz}',
                     '-do','onerror {quit -code 1}; run -all; quit -f'],c,'simulation',1200)
        except RuntimeError:
            if not expected:raise
            log=(c/'simulation.log').read_text(errors='replace')
        if expected:
            assert '** Fatal:' in log and expected in log,log[-2000:]
            marker='EXPECTED_FAILURE '+expected
        else:
            assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
            m=re.search(r'PASS_DIAG_MEMORY[^\r\n]*',log);assert m,log[-2000:]
            assert 'cancels=9' in m[0]
            marker=m[0]
        result=dict(name=name,total=total,ad=ad,cd=cd,dd=dd,dq=dq,hz=hz,mutation=mutation,
                    expected_failure=expected,marker=marker,sources={f:sha(c/f) for f in files})
        results.append(result);put(out/'progress.json',json.dumps(results,indent=2)+'\n')
        print(marker,flush=True)
    put(out/'result.json',json.dumps(dict(candidate='NES-DIAG-MEMORY-067',cases=results,
        physical_execution=False,fit_sta=False,pin_delay_assumptions_ns=[0,2,20],outside_bound_ns=126,
        scope='full geometry loader/CHECK pin model; not SPI/MCU, fitted IO or board measurement'),indent=2)+'\n')


if __name__=='__main__':main()
