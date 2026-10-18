# SPDX-License-Identifier: MIT
"""Directed host-fixture grouping boundaries; not a producer RTL fault test."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from prepare_nes_coalesce247 import COALESCE
from nes_delta231 import sha

HARNESS=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static bool bulk232(unsigned,unsigned,unsigned,const uint8_t *,unsigned);
@HELPER@
static bool bulk232(unsigned kind,unsigned slot,unsigned gen,const uint8_t *p,unsigned n){
 unsigned unit=kind?32:16;assert(n&&n<=2048&&n%unit==0);
 for(unsigned i=0;i<n;i++)assert(p[i]==(uint8_t)(gen*17+kind*31+(slot+i/unit)*7+i%unit));
 return true;
}
static void tile(unsigned kind,unsigned slot,unsigned gen){
 uint8_t b[32];unsigned n=kind?32:16;
 for(unsigned i=0;i<n;i++)b[i]=(uint8_t)(gen*17+kind*31+slot*7+i);
 assert(chunk_queue247(kind,slot,gen,b,n));
}
int main(void){
 chunks247=fopen("chunks.csv","w");assert(chunks247);
 fprintf(chunks247,"generation,kind,slot,bytes\n");
 /* No flush at15-record batches:130 BG tiles force2048+32. */
 for(unsigned i=0;i<130;i++)tile(0,i,1);assert(chunk_flush247());
 for(unsigned i=0;i<128;i++)tile(1,i,2);assert(chunk_flush247());
 tile(0,5,3);tile(0,6,3);tile(0,8,3);tile(0,7,3);
 tile(1,7,3);tile(1,8,3);tile(0,7,3);assert(chunk_flush247());
 tile(0,2,4);assert(chunk_flush247());assert(chunk_flush247());
 tile(0,2,5);assert(chunk_flush247());fclose(chunks247);return 0;
}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    (out/'test.c').write_text(HARNESS.replace('@HELPER@',COALESCE),encoding='utf-8',newline='\n')
    env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
    commands=[[str(a.gcc),'-std=c11','-Wall','-Wextra','-Werror','-O2','test.c','-o','test.exe'],[str(out/'test.exe')]]
    for cmd,name in zip(commands,('build','run')):
        with (out/(name+'.log')).open('wb') as log:
            done=subprocess.run(cmd,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        assert done.returncode==0,(name,(out/(name+'.log')).read_text(errors='replace'))
    expected=[(1,0,0,2048),(1,0,128,32),(2,1,0,2048),(2,1,64,2048),
              (3,0,5,32),(3,0,8,16),(3,0,7,16),(3,1,7,64),(3,0,7,16),(4,0,2,16),(5,0,2,16)]
    actual=[tuple(map(int,line.split(','))) for line in (out/'chunks.csv').read_text().splitlines()[1:]]
    assert actual==expected
    result=dict(passed=True,cases=4,chunks=len(actual),payload_bytes=sum(x[3] for x in actual),scope=__doc__,
                helper_sha256=__import__('hashlib').sha256(COALESCE.encode()).hexdigest(),script_sha256=sha(Path(__file__)),
                output_hashes={n:sha(out/n) for n in ('test.c','test.exe','build.log','run.log','chunks.csv')})
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');shutil.copyfile(__file__,out/'test.py')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
