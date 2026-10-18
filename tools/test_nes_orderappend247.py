# SPDX-License-Identifier: MIT
"""Exercise actual plan-service append/CRC/END with bounded in-place ordering."""
from pathlib import Path
import argparse,json,os,shutil,struct,subprocess
from nes_delta231 import BASE,sha,once
from nes_batchorder247 import HEADER

HOST=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "service247.c"
static FILE *sent247;static unsigned accepted247;static bool ended247;
bool nes_sink195_bulk(struct nes_native_sink165 *s,const uint8_t d[12]){(void)s;(void)d;assert(0);return false;}
static bool guard247(void *p){(void)p;return true;}
static bool transfer247(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 (void)ctx;
 if(tx[0]==0xe8){
  assert(n==20);memset(rx,0,n);rx[1]=0xd7;rx[2]=4;rx[3]=ended247?2:1;
  rx[4]=(uint8_t)(accepted247>>8);rx[5]=(uint8_t)accepted247;rx[19]=crc8(rx+1,18);return true;
 }
 assert(tx[0]==0xe9&&!ended247&&n<=248);unsigned size=tx[1]+256u*tx[2];assert(n==size+8&&tx[3]<=15);
 assert(crc16(tx+4,size)==(unsigned)tx[size+4]*256+tx[size+5]&&crc8(tx,size+6)==tx[size+6]&&tx[size+7]==0xa5);
 assert(fwrite(tx,1,n,sent247)==n);
 unsigned at=0,count=0;while(at<size){unsigned key=order247_key(tx+4+at);if(key==65535){assert(at+3==size);ended247=true;}at+=order247_length(tx+4+at);count++;}
 assert(at==size&&count==tx[3]);accepted247++;memset(rx,0,n);return true;
}
int main(void){
 assert(sizeof(struct nes_plan191)==40);FILE *f=fopen("cases.bin","rb");assert(f);
 for(unsigned test=0;test<4;test++){
  unsigned char b[2];assert(fread(b,1,2,f)==2);unsigned count=b[0]+256u*b[1];
  char name[64];sprintf(name,"case%u.bin",test);sent247=fopen(name,"wb");assert(sent247);
  struct nes_native_sink165 sink={0};sink.state=NES_SINK165_BUILD;sink.generation=9;
  struct {unsigned before;struct nes_plan200 p;unsigned after;} guarded={0};guarded.before=0x12345678;guarded.after=0x87654321;
  struct nes_plan200 *p=&guarded.p;p->sink=&sink;p->transfer=transfer247;p->guard=guard247;p->poll_limit=4;
  accepted247=0;ended247=false;
  for(unsigned i=0;i<count;i++){struct nes_plan191 q;assert(fread(&q,1,40,f)==40);assert(nes_plan200_emit(p,&q));}
  assert(nes_plan200_finish(p)&&p->finished&&ended247&&!p->count&&!p->bytes);
  assert(guarded.before==0x12345678&&guarded.after==0x87654321);fclose(sent247);
 }
 assert(fgetc(f)==EOF);fclose(f);puts("PASS actual append/flush/CRC/END:4 bounded mixed-record cases");return 0;
}
'''


def q(kind,slot=0,alts=0,nonidentity=False):
    rows=[i//2 for i in range(16)] if kind<2 else [0]*16
    if nonidentity:rows[0]=7
    alt=[200+i if i<alts else 65535 for i in range(8)]
    return struct.pack('<HHHBB16B8H',9,slot,100 if kind<2 else 0,kind,255 if kind<2 else 0,*rows,*alt)


def records(wire):
    out=[];at=0
    while at<len(wire):
        kind=wire[at]&3
        n=(7 if kind==0 else 8 if kind==1 else 3) if wire[at]&128 else 16+2*wire[at+1].bit_count()
        value=wire[at:at+n];assert len(value)==n
        offset=3 if value[0]&128 else 4
        key=(kind*1024+int.from_bytes(value[offset:offset+2],'little')) if kind<2 else 0 if kind==2 else 65535
        out.append((key,value));at+=n
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);src=BASE/'probes/nes-runtime233/arm01/src';pins={}
    for f in src.glob('*.h'):shutil.copyfile(f,out/f.name)
    service=src/'nes_plan_service200.c';pins[service.relative_to(BASE).as_posix()]=sha(service)
    s=once(service.read_text(),'#include <string.h>','#include <string.h>\n#include "order247.h"')
    original=s
    s=once(s,'memcpy(p->buffer+4+p->bytes,encoded,n);','order247_insert(p->buffer+4,p->bytes,encoded,n);')
    (out/'service247.c').write_text(s,encoding='utf-8',newline='\n');(out/'order247.h').write_text(HEADER,encoding='utf-8',newline='\n')
    (out/'host.c').write_text(HOST,encoding='utf-8',newline='\n')
    cases=[[q(0,i) for i in range(15,0,-1)],
           [q(0,30-i,i,True) for i in range(9)]+[q(1,5),q(2)],
           [q(0,20-i,8,True) for i in range(7)]+[q(1,6),q(1,5)],
           [q(2)]+[q(1,i) for i in range(14,0,-1)]+[q(0,1,0,True)]]
    (out/'cases.bin').write_bytes(b''.join(struct.pack('<H',len(c))+b''.join(c) for c in cases))
    env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
    def run(args,label):
        with (out/(label+'.log')).open('wb') as log:r=subprocess.run(list(map(str,args)),cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        assert r.returncode==0,(out/(label+'.log')).read_text(errors='replace')
    run([a.gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','host.c','-o','sorted.exe'],'build-sorted');run([out/'sorted.exe'],'run-sorted')
    sorted_wire=[(out/f'case{i}.bin').read_bytes() for i in range(4)]
    for i,b in enumerate(sorted_wire):(out/f'sorted{i}.bin').write_bytes(b)
    (out/'service247.c').write_text(original,encoding='utf-8',newline='\n')
    # Keep helper definitions referenced by the capture decoder; insertion is
    # intentionally absent from the reference append and may be unused.
    run([a.gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','host.c','-o','original.exe'],'build-original');run([out/'original.exe'],'run-original')
    counts=[]
    def batches(b):
        result=[];at=0
        while at<len(b):
            n=int.from_bytes(b[at+1:at+3],'little');result.append(records(b[at+4:at+4+n]));at+=n+8
        assert at==len(b);return result
    for i,b in enumerate(sorted_wire):
        before=batches((out/f'case{i}.bin').read_bytes());after=batches(b);assert len(before)==len(after)
        for x,y in zip(before,after):assert sorted(x,key=lambda r:r[0])==y
        counts.append([len(v) for v in after])
    (out/'service247.c').write_text(s,encoding='utf-8',newline='\n')
    r=dict(passed=True,cases=4,batch_record_counts=counts,actual_plan_service_append=True,
           crc_checked=True,end_last=True,original_batch_boundaries_and_record_bytes_exact=True,
           canaries_pass=True,persistent_state_added=0,arm_run_irq_verified=False,scope=__doc__,
           input_hashes=pins,helper_sha256=sha(out/'order247.h'),script_sha256=sha(Path(__file__)))
    (out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');shutil.copyfile(__file__,out/'test.py');print(json.dumps(r,indent=2))


if __name__=='__main__':main()
