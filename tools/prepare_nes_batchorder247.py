# SPDX-License-Identifier: MIT
"""Build private C replay with bounded encoded batch ordering; fixture storage is host-only."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_delta231 import BASE,sha,once
from nes_batchorder247 import HEADER

QUEUE=r'''
#include "nes_plan_wire199.h"
#include "order247.h"
static uint8_t order_buffer247[240];static unsigned order_bytes247,order_count247;
/* Host-only converted-pixel fixture, NOT proposed ARM storage. */
static struct {unsigned key,kind,slot,gen,n;uint8_t bytes[32];} fixture247[15];
static FILE *order_log247;
static bool order_flush247(void){
 unsigned at=0;for(unsigned i=0;i<order_count247;i++){
  unsigned key=order247_key(order_buffer247+at),n=order247_length(order_buffer247+at);at+=n;
  unsigned j=0;while(j<order_count247&&fixture247[j].key!=key)j++;assert(j<order_count247);
  fprintf(order_log247,"%u,%u,%u,%u\n",fixture247[j].gen,fixture247[j].kind,fixture247[j].slot,n);fflush(order_log247);
  if(!bulk232(fixture247[j].kind,fixture247[j].slot,fixture247[j].gen,fixture247[j].bytes,fixture247[j].n))return false;
 }
 assert(at==order_bytes247);order_bytes247=order_count247=0;return true;
}
static bool order_queue247(const struct nes_plan191 *q,const uint8_t *bytes,unsigned unit){
 uint8_t encoded[32];unsigned n=nes_plan199_encode(q,encoded);assert(n);
 if(order_count247==15||order_bytes247+n>240)if(!order_flush247())return false;
 unsigned i=order_count247;fixture247[i].key=order247_key(encoded);fixture247[i].kind=q->kind==1;
 fixture247[i].slot=q->slot;fixture247[i].gen=q->generation;fixture247[i].n=unit;memcpy(fixture247[i].bytes,bytes,unit);
 order247_insert(order_buffer247,order_bytes247,encoded,n);order_bytes247+=n;order_count247++;
 return order_count247<15||order_flush247();
}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    old=BASE/'probes/nes-sparse232/scroll02/common';pins={}
    for f in old.iterdir():
        if f.suffix in ('.c','.h','.inc'):
            shutil.copyfile(f,out/f.name);pins[f.relative_to(BASE).as_posix()]=sha(f)
    for n in ('nes_plan_wire196.h','nes_plan_wire199.h'):
        f=BASE/'probes/nes-runtime233/arm01/src'/n;shutil.copyfile(f,out/n);pins[f.relative_to(BASE).as_posix()]=sha(f)
    (out/'order247.h').write_text(HEADER,encoding='utf-8',newline='\n')
    f=out/'host.c';s=f.read_text()
    s=once(s,'static bool write_slot(',QUEUE+'\nstatic bool write_slot(')
    s=once(s,'return bulk232(kind,q->slot,q->generation,out,unit);','return order_queue247(q,out,unit);')
    s=once(s,'static void cost225(void){','static void cost225(void){\n assert(order_flush247());')
    s=once(s,' assert(argc==6);', ' order_log247=fopen("order247.csv","w");assert(order_log247);fprintf(order_log247,"generation,kind,slot,encoded_bytes\\n");\n assert(argc==6);')
    f.write_text(s,encoding='utf-8',newline='\n')
    env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
    files=['host.c','reference203.c','nes_planner211.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_native_sink165.c','nes_sink_trace168.c','nes_delta231.c']
    with (out/'build.log').open('wb') as log:r=subprocess.run([str(a.gcc),'-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'-o','host.exe'],cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode==0,(out/'build.log').read_text(errors='replace')
    result=dict(passed=True,scope=__doc__,product_changed=False,full_arm=False,input_hashes=pins,
                host_only_fixture_bytes='15 converted tiles;not ARM allocation',helper_bytes=len(HEADER.encode()),
                output_hashes={n:sha(out/n) for n in files+['order247.h','host.exe','build.log']},script_sha256=sha(Path(__file__)))
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');shutil.copyfile(__file__,out/'prepare.py')
    print('PASS: private bounded-batch C replay compiled; not full ARM runtime.')


if __name__=='__main__':main()
