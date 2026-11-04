"""Run the OBJ-only dual-port replay or measure its Quartus Lite region."""
import argparse
from pathlib import Path
import json
import re
import shutil
import subprocess

from check_nes_wire600 import ROOT, pin, read, sha


def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    top='nes_obj_capture609'
    rtl=ROOT/'rtl'/(top+'.sv')
    bench=ROOT/'tools'/(top+'_tb.sv')
    shutil.copy(rtl,a.out)
    def command(args,name):
        with (a.out/(name+'.log')).open('wb') as log:
            subprocess.run(args,cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
    result=dict(RTL=sha(rtl))
    if a.mode=='sim':
        pin(a.fixture,read(ROOT/'analysis/snoop601-verification.json')['fixture_sha256'])
        shutil.copy(a.fixture,a.out/'stim.tsv')
        shutil.copy(bench,a.out)
        command([a.bin/'vlib.exe','work'],'lib')
        command([a.bin/'vlog.exe','-sv',rtl.name,bench.name],'compile')
        command([a.bin/'vsim.exe','-c',top+'_tb','-do','onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0'],'sim')
        match=re.search(r'PASS609 fills=(\d+) queries=(\d+) hits=(\d+) concurrent=(\d+)',(a.out/'sim.log').read_text())
        assert match
        result.update(zip(('fills','queries','hits','concurrent'),map(int,match.groups())))
        result.update(fixture=sha(a.fixture),bench=sha(bench),log=sha(a.out/'sim.log'))
    else:
        (a.out/'region.qpf').write_text('PROJECT_REVISION = "region"\n')
        (a.out/'region.qsf').write_text(f'set_global_assignment -name FAMILY "Cyclone IV E"\nset_global_assignment -name DEVICE EP4CE15F17C8\nset_global_assignment -name TOP_LEVEL_ENTITY {top}\nset_global_assignment -name SYSTEMVERILOG_FILE {rtl.name}\n')
        command([a.bin/'quartus_map.exe','region'],'map')
        summary=(a.out/'region.map.summary').read_text()
        assert 'Successful' in summary and 'Lite Edition' in summary
        for key,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('bits','Total memory bits')]:
            result[key]=int(re.search(r'^\s*'+label+r'\s*:\s*([\d,]+)',summary,re.M)[1].replace(',',''))
        result['report']=sha(a.out/'region.map.rpt')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['sim','map'])
    for n in ('bin','out','fixture'):p.add_argument('--'+n,type=Path,required=n!='fixture')
    run(p.parse_args())
