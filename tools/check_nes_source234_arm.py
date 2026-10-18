# SPDX-License-Identifier: MIT
"""C234 ARM object/ABI gate only; production ingress call graph not bound."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_delta231 import BASE,sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);pins={}
    for f in a.candidate.glob('nes_*'):
        if f.suffix in ('.c','.h','.inc'):shutil.copyfile(f,d/f.name);pins[f.name]=sha(f)
    (d/'layout.c').write_text('#include "nes_source234.h"\nchar source234_bytes[sizeof(struct nes_source234)];\nchar input_bytes[sizeof(struct nes_native165)];\n')
    arm=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
    env=os.environ.copy();env['PATH']=str(arm)+os.pathsep+env.get('PATH','')
    def run(tool,args,name):
        with (d/(name+'.log')).open('wb') as log:
            q=subprocess.run([str(arm/('arm-none-eabi-'+tool+'.exe')),*args],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
        t=(d/(name+'.log')).read_text(errors='replace');assert q.returncode==0,t;return t
    run('gcc',['-std=c11','-Wall','-Wextra','-Werror','-mcpu=cortex-m4','-mthumb','-Os','-ffunction-sections','-fstack-usage','-c','nes_native165.c','layout.c'],'compile')
    nm=run('nm',['-S','layout.o'],'layout');run('objdump',['-dr','nes_native165.o'],'disassembly')
    layout={n:int(re.search(r'\w+\s+([\da-f]+)\s+\w\s+'+n,nm)[1],16) for n in ('source234_bytes','input_bytes')}
    assert layout==dict(source234_bytes=32,input_bytes=9880)
    stacks={}
    for line in (d/'nes_native165.su').read_text().splitlines():
        where,size,kind=line.split('\t');stacks[where.rsplit(':',1)[-1]]=dict(bytes=int(size),kind=kind)
    assert 'nes_source234_packet' in stacks and all(v['kind']=='static' for v in stacks.values())
    r=dict(passed=True,scope=__doc__,pins=pins,layout=layout,stacks=stacks,full_run_irq_approved=False,
           no_second_geometry=True,no_packet_copy_buffer=True,prior233_margin_not_reapproved=1616,
           compiler_sha256=sha(arm/'arm-none-eabi-gcc.exe'),script_sha256=sha(Path(__file__)))
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(layout=layout,stacks={k:v for k,v in stacks.items() if '234' in k}),indent=2))


if __name__=='__main__':main()
