# SPDX-License-Identifier: MIT
"""Measure candidate objects/ARM ABI only; no linked RUN/consumer approval."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_resident211 import sha
def main():
    p=argparse.ArgumentParser()
    for name in ['candidate','arm-bin','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.arm_bin=a.arm_bin.resolve();a.candidate=a.candidate.resolve();a.out.mkdir(parents=True,exist_ok=False)
    pins={}
    for f in a.candidate.glob('nes_*'):
        if f.suffix in ['.c','.h']:
            shutil.copyfile(f,a.out/f.name);pins[f.name]=sha(f)
    (a.out/'layout.c').write_text('#include "nes_resident211.h"\nchar resident_bytes[sizeof(struct nes_resident211)];\nchar video_bytes[sizeof(struct nes_native_video165)];\n',encoding='utf8')
    env=os.environ.copy();env['PATH']=str(a.arm_bin)+os.pathsep+env.get('PATH','')
    def run(tool,args,name):
        with (a.out/(name+'.log')).open('wb') as log:
            r=subprocess.run([str(a.arm_bin/('arm-none-eabi-'+tool+'.exe')),*args],cwd=a.out,env=env,
                             stdout=log,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        text=(a.out/(name+'.log')).read_text(errors='replace');assert not r.returncode,text;return text
    objects=['nes_resident211','nes_planner211','nes_plan191']
    run('gcc',['-std=c11','-Wall','-Wextra','-Werror','-mcpu=cortex-m4','-mthumb','-Os',
               '-fstack-usage','-c',*[x+'.c' for x in objects],'layout.c'],'compile')
    nm=run('nm',['-S','layout.o'],'layout')
    layout={name:int(re.search(r'\w+\s+([\da-f]+)\s+\w\s+'+name,nm)[1],16) for name in ['resident_bytes','video_bytes']}
    sizes=run('size',[x+'.o' for x in objects],'sizes')
    stacks={}
    for f in a.out.glob('*.su'):
        for line in f.read_text().splitlines():
            where,size,kind=line.split('\t');stacks[where.rsplit(':',1)[-1]]=dict(bytes=int(size),kind=kind)
    assert layout['video_bytes']==15912
    assert layout['resident_bytes']<=3328
    result=dict(passed=True,input_pins=pins,layout=layout,sizes=sizes,stacks=stacks,
                replaces_passive_model_bytes=2560,retained_state_delta=layout['resident_bytes']-2560,
                old_margin210=5744,arithmetic_margin_before_callchain_and_protocol=5744-(layout['resident_bytes']-2560),
                full_runtime_approved=False,spi_snes_consumer_integrated=False,
                scope=__doc__,script_sha256=sha(Path(__file__)))
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result))
if __name__=='__main__':main()
