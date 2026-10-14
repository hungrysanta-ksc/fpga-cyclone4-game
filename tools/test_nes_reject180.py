# SPDX-License-Identifier: MIT
"""Actual SPI ring with selective samples, plus unchanged collector release."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha


def main():
    p=argparse.ArgumentParser()
    for n in ['candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    assert not a.out.exists();a.out.mkdir(parents=True)
    m=json.loads((a.candidate/'preparation.json').read_bytes())
    for n,h in m['sources'].items():
        assert sha(a.candidate/n)==h,n
        (a.out/n).parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(a.candidate/n,a.out/n)
    tbs=['reject180_tb.sv','native_release177_tb.sv']
    for n in tbs:shutil.copy2(ROOT/'tests/nes-functional'/n,a.out/n)
    # Compile the complete candidate, not only a disconnected observer fixture.
    files=re.findall(r'-name (?:SYSTEMVERILOG|VERILOG)_FILE (\S+)',(a.out/'board.qsf').read_text())
    logs={}
    def run(exe,args,label):
        with (a.out/(label+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
        s=(a.out/(label+'.log')).read_text(errors='replace')
        assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4000:]
        logs[label]=sha(a.out/(label+'.log'));return s
    run('vlib',['work'],'vlib')
    run('vlog',['-sv','-mfcu',*files,*tbs],'vlog')
    for top,marker in [('reject180_tb','PASS180 witness'),('native_release177_tb','PASS RELEASE177 cases=14 checks=42')]:
        s=run('vsim',['-c','work.'+top,'-do','onerror {quit -code 1}; run -all; quit -f'],top)
        assert marker in s;print(marker,flush=True)
    result=dict(passed=True,sources=m['sources'],logs=logs,public_sources={n:sha(ROOT/n) for n in
        ['tools/test_nes_reject180.py',*['tests/nes-functional/'+n for n in tbs]]},
        scope=__doc__,hardware=False,video_fix=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
