# SPDX-License-Identifier: MIT
"""Cycle comparison of prepared rank candidate and frozen board181 map03."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','board','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    n='nes_native_compact181.sv';base=ROOT/'analysis/board181-verification.json'
    assert sha(a.baseline/n)==json.loads(base.read_bytes())['verification']['fits']['map03']['sources'][n]
    assert sha(a.board/n)==json.loads((a.board/'preparation.json').read_bytes())['sources'][n]
    a.out.mkdir(parents=True);shutil.copy2(a.board/n,a.out/n)
    (a.out/'original.sv').write_text((a.baseline/n).read_text().replace('module nes_native_compact181(','module compact181_original('),encoding='utf8')
    tb=ROOT/'tests/nes-functional/rank181_tb.sv';shutil.copy2(tb,a.out/'bench.sv')
    def run(exe,args):
        with (a.out/(exe+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=240)
        s=(a.out/(exe+'.log')).read_text(errors='replace')
        assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-5000:]
        return s
    run('vlib',['work']);run('vlog',['-sv',n,'original.sv','bench.sv'])
    s=run('vsim',['-c','work.rank181_tb','-do','onerror {quit -code 1}; run -all; quit -f'])
    m=re.search(r'PASS RANK181 cycles=(\d+) scenes=(\d+) same=(\d+) new=(\d+) reads=(\d+)',s);assert m
    result=dict(passed=True,counts=dict(zip(['cycles','scenes','same','new','reads'],map(int,m.groups()))),
        baseline_sha256=sha(a.baseline/n),candidate_sha256=sha(a.board/n),bench_sha256=sha(tb),runner_sha256=sha(Path(__file__)),
        scope='Synthetic complete compact scenes plus deterministic malformed/control stress; all output ports cycle-compared. Not formal or full-game proof.',hardware=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(m[0])

if __name__=='__main__':main()
