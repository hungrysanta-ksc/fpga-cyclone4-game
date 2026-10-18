# SPDX-License-Identifier: MIT
"""ARM object ABI/stack preflight only, not linked RUN/IRQ or firmware approval."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_delta231 import sha,BASE


def main():
    p=argparse.ArgumentParser()
    for n in ('candidate','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);pins={}
    for f in a.candidate.glob('nes_*'):
        if f.suffix in ('.c','.h','.inc'):shutil.copyfile(f,d/f.name);pins[f.name]=sha(f)
    (d/'layout.c').write_text('#include "nes_delta231.h"\nchar source_bytes[sizeof(struct nes_source231)];\nchar dirty_bytes[sizeof(struct nes_dirty231)];\nchar input_bytes[sizeof(struct nes_native165)];\nchar video_bytes[sizeof(struct nes_native_video165)];\n')
    arm=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
    env=os.environ.copy();env['PATH']=str(arm)+os.pathsep+env.get('PATH','')
    def run(tool,args,name):
        with (d/(name+'.log')).open('wb') as log:
            q=subprocess.run([str(arm/('arm-none-eabi-'+tool+'.exe')),*args],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
        text=(d/(name+'.log')).read_text(errors='replace');assert q.returncode==0,text;return text
    objects=['nes_native165','nes_planner211','nes_native_sink165','nes_delta231']
    run('gcc',['-std=c11','-Wall','-Wextra','-Werror','-mcpu=cortex-m4','-mthumb','-Os','-fstack-usage','-c',*[n+'.c' for n in objects],'layout.c'],'compile')
    nm=run('nm',['-S','layout.o'],'layout');sizes=run('size',[n+'.o' for n in objects],'sizes')
    layout={n:int(re.search(r'\w+\s+([\da-f]+)\s+\w\s+'+n,nm)[1],16) for n in ('source_bytes','dirty_bytes','input_bytes','video_bytes')}
    stacks={}
    for f in d.glob('*.su'):
        for line in f.read_text().splitlines():
            where,size,kind=line.split('\t');stacks[where.rsplit(':',1)[-1]]=dict(bytes=int(size),kind=kind)
    assert layout==dict(source_bytes=36,dirty_bytes=124,input_bytes=9880,video_bytes=15912)
    result=dict(passed=True,scope=__doc__,pins=pins,layout=layout,stacks=stacks,object_sizes=sizes,extra_retained_bytes=160,
                original_margin=1800,arithmetic_margin_before_extra_callchain=1640,full_run_irq_approved=False,
                compiler_sha256=sha(arm/'arm-none-eabi-gcc.exe'),script_sha256=sha(Path(__file__)))
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
