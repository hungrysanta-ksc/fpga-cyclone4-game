# SPDX-License-Identifier: MIT
"""Bounded connected audit: sticky arbiter fault versus pre-BEGIN silence."""
import argparse,json,os,re,shutil,subprocess
from pathlib import Path
from nes_game147 import ROOT,sha

def main():
    p=argparse.ArgumentParser()
    for n in ['deployed','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    pins=json.loads((ROOT/'analysis/errorzero174-verification.json').read_bytes())['sources']
    names=['nes_native_arbiter165.sv','nes_native_export165.sv','nes_live_joint.sv']
    for n in names:assert sha(a.deployed/n)==pins[n],n
    joint=(a.deployed/'nes_live_joint.sv').read_text()
    assert joint.count('.geometry_valid(native_geometry_valid&&!rom_fault&&!native_arbiter_fault)')==2
    assert 'assign out_fault=fault;' in joint
    a.out.mkdir(parents=True)
    for n in names[:2]:shutil.copy2(a.deployed/n,a.out/n)
    bench='tests/nes-functional/native_fault176_tb.sv'
    shutil.copy2(ROOT/bench,a.out/'native_fault176_tb.sv')
    logs={}
    for exe,args,label in [('vlib',['work'],'vlib'),('vlog',['-sv',*names[:2],'native_fault176_tb.sv'],'vlog'),
                           ('vsim',['-c','work.native_fault176_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'sim')]:
        with (a.out/(label+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=120)
        text=(a.out/(label+'.log')).read_text(errors='replace')
        assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-3000:]
        logs[label]=sha(a.out/(label+'.log'))
    match=re.search(r'PASS FAULT176 cases=(\d+) checks=(\d+)',text);assert match
    result=dict(passed=True,cases=int(match[1]),checks=int(match[2]),sources={n:pins[n] for n in names},
                public_sources={n:sha(ROOT/n) for n in [bench,'tools/test_nes_fault176.py']},logs=logs,
                scope='Exact174 arbiter/exporter, synthetic requests/replies/raw-valid geometry. Timeout/backend/address injections before admission or after BEGIN. No actual fill/CPU/physical reader/COMMIT sequence or hardware-cause proof.',
                conclusion='Sticky fault can silence later BEGIN with core replies alive, BUT an in-flight fault emits ABORT1 first. Hardware174 ABORT0 therefore does not establish this cause; do not remove the watchdog.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()
