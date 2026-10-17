# SPDX-License-Identifier: MIT
"""Actual C planner/reference + modeled dual destination consumer. No FIT/FPS."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_resident211 import prepare,sha,ROOT
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out=a.out.resolve();pins=prepare(a.out)
    gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
    env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
    def run(cmd,name):
        with (a.out/(name+'.log')).open('wb') as log:
            r=subprocess.run(list(map(str,cmd)),cwd=a.out,env=env,stdout=log,stderr=subprocess.STDOUT,
                             timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        text=(a.out/(name+'.log')).read_text(errors='replace');assert r.returncode==0,text[-6000:]
        return text
    files=['resident211_host.c','nes_resident211.c','nes_planner211.c','nes_native165.c','nes_trace166.c','reference203.c']
    run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'-o','host.exe'],'build')
    result=run([a.out/'host.exe'],'host');assert 'PASS RESIDENT211' in result
    report=dict(candidate=211,preparation_sha256=sha(a.out/'preparation.json'),output=result,
                logs={n:sha(a.out/n) for n in ['build.log','host.log']},
                scope='Actual210 geometry planner and actual186 reference converter; arbitrary-slot writes and dual-bank consumer modeled in C. Synthetic scrolling only, no gameplay/FPS/SPI/65816/FIT proof.',
                sources={str(f.relative_to(ROOT)):sha(f) for f in [Path(__file__),ROOT/'tools/nes_resident211.py']},
                deployable=False)
    (a.out/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(result)
if __name__=='__main__':main()
