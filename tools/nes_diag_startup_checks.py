# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,os,re,shutil
from nes_spi_boot import ROOT,put,run,sha
from nes_rom_geometry import replace

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True)
    a=p.parse_args();assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
    out=a.out.resolve();out.mkdir(exist_ok=False,parents=True);shutil.copy2(__file__,out/'executed-driver.py')
    cases=[]
    for name,half,short,expected in [('board8',None,False,None),('max10',50,False,None),
              ('short-wait',None,True,'STARTUP_EDGE_COUNT'),('outside16',31,False,'STARTUP_BEFORE_150US')]:
        c=out/name;c.mkdir();s=(ROOT/'src/nes/diagnostic/nes_diag_startup_guard.sv').read_text()
        if short:s=replace(s,'WAIT_CYCLES=1600','WAIT_CYCLES=1')
        put(c/'nes_diag_startup_guard.sv',s);shutil.copy2(ROOT/'tests/nes-functional/diag_startup_guard_tb.sv',c/'diag_startup_guard_tb.sv')
        for tool,args in [('vlib',['work']),('vlog',['-sv','nes_diag_startup_guard.sv','diag_startup_guard_tb.sv'])]:
            log=run([a.questa_bin/(tool+'.exe'),*args],c,tool)
            assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
        args=['+HALF='+str(half)] if half else []
        try:log=run([a.questa_bin/'vsim.exe','-c','-t','1ps','diag_startup_guard_tb',*args,'-do','onerror {quit -code 1}; run -all; quit -f'],c,'simulation',300)
        except RuntimeError:
            if not expected:raise
            log=(c/'simulation.log').read_text(errors='replace')
        if expected:assert '** Fatal:' in log and expected in log;marker='EXPECTED_FAILURE '+expected
        else:
            assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
            m=re.search(r'PASS_STARTUP_GUARD[^\r\n]*',log);assert m;marker=m[0]
        cases.append(dict(name=name,expected_failure=expected,marker=marker,sources={n:sha(c/n) for n in ['nes_diag_startup_guard.sv','diag_startup_guard_tb.sv']}))
        print(marker,flush=True)
    put(out/'result.json',json.dumps(dict(candidate='NES-DIAG-SAFETY-068',cases=cases,physical_execution=False),indent=2)+'\n')
if __name__=='__main__':main()
