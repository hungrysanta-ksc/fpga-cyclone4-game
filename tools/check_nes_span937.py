"""Differential test of the exact C packet boundary selectors on this ARM link."""
import json
import os
from pathlib import Path
import subprocess
import sys
from nes_oam937 import base, work
from nes_raw506 import sha


def functions(link):
    text=(link/'src/nes_native_sink165.c').read_text()
    return text[text.index('static unsigned repeat_bytes('):text.index('static bool span(')]


MAIN=r'''
static uint32_t state=937;
static unsigned random_byte(void){state=1664525u*state+1013904223u;return state>>24;}
static unsigned cases;
static uint8_t b[4096];
static void check(unsigned n){
    unsigned a=reference(b,n), c=span_piece(b,n);
    if(a!=c || !a || a>n){fprintf(stderr,"n=%u expected=%u got=%u\n",n,a,c);exit(1);}
    ++cases;
}
int main(void){
    /* Include odd starts, the 239/240 split, almost-runs, overlapping
       runs after a mismatch and buffers ending on either byte of a word. */
    for(unsigned i=0;i<=242;++i)for(unsigned n=61;n<=67;++n){
        for(unsigned j=0;j<sizeof b;++j)b[j]=j;
        for(unsigned j=0;j<n;++j)b[i+j]=(j&1)?0x26:0x9b;
        check(i+n);check(i+n+1);check(512);
        for(unsigned j=0;j<n;++j){b[i+j]^=0xf0;check(i+n);b[i+j]^=0xf0;}
    }
    for(unsigned n=1;n<=sizeof b;++n){
        for(unsigned j=0;j<n;++j)b[j]=(j&1)?0xff:0x01;
        check(n);
        for(unsigned j=0;j<n;++j)b[j]=random_byte();
        check(n);
        if(n>=64){
            unsigned pos=random_byte()%(n-63);
            for(unsigned j=0;j<64;++j)b[pos+j]=j&1;
            check(n);
        }
    }
    printf("%u\n",cases);return 0;
}
'''


def run(mode):
    path=work(mode)/'span-check'
    path.mkdir(exist_ok=True)
    before=functions(base('batchfast')/'link').replace('repeat_bytes','reference_run').replace('span_piece','reference')
    after=functions(work(mode)/'link')
    source=path/'compare.c'
    source.write_text('#include <stdint.h>\n#include <stdio.h>\n#include <stdlib.h>\n'+before+after+MAIN,encoding='ascii')
    gcc=Path('C:/altera_lite/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
    env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ['PATH'])
    exe=path/'compare.exe'
    subprocess.run([gcc,'-std=c99','-O2',source,'-o',exe],env=env,check=True)
    cases=int(subprocess.check_output([exe],env=env,text=True))
    result=dict(cases=cases,source_sha256=sha(source),firmware_sha256=sha(work(mode)/'link/src/obj-nes-100/firmware.stm'))
    (path/'result.json').write_text(json.dumps(result)+'\n')
    print(result)


if __name__=='__main__':
    run(sys.argv[1])
