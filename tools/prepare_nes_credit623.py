# SPDX-License-Identifier: MIT
"""Publish palette offset 128 after a checked drain of the two leading packets."""
import argparse
import re
import shutil
from pathlib import Path

from nes_raw506 import once, sha


def share_report(src):
    header=src/'nes_cost471.h'
    header.write_bytes(once(header.read_text(),'int nes_cost471_append(','''int nes_report623(char *,unsigned,int,const char *,...) __attribute__((format(printf,4,5)));
int nes_cost471_append(''').encode())
    path=src/'nes_cost471.c'
    code=path.read_text()
    begin=code.index('int nes_cost471_append(')
    end=code.index('/* Called only between',begin)
    report=code[begin:end].replace('int z=snprintf(text+n,size-(unsigned)n,','n=nes_report623(text,size,n,').replace('z=snprintf(text+n,size-(unsigned)n,','n=nes_report623(text,size,n,')
    report=once(report,'return z<0||(unsigned)z>=size-(unsigned)n?-1:n+z;','return n;')
    report,n=re.subn(r'if\(z<0\|\|\(unsigned\)z>=size-\(unsigned\)n\)return -1;\s*n\+=z;', 'if(n<0)return -1;',report)
    assert n==4
    helper='''int nes_report623(char *text,unsigned size,int at,const char *format,...){
 if(at<0||(unsigned)at>=size)return -1;
 va_list args;va_start(args,format);
 int used=vsnprintf(text+at,size-(unsigned)at,format,args);
 va_end(args);
 return used<0||(unsigned)used>=size-(unsigned)at?-1:at+used;
}
'''
    path.write_bytes(('#include <stdarg.h>\n'+code[:begin]+helper+report+code[end:]).encode())
    path=src/'nes_budget210.c'
    code=path.read_text()
    code=once(code,'int n=snprintf(text,size,','int n=nes_report623(text,size,0,')
    code=once(code,'if(n<0||(unsigned)n>=size)return -1;','if(n<0)return -1;')
    for k in ('post','cause','used'):
        code=code.replace(f'int {k}=snprintf(text+n,size-(unsigned)n,','n=nes_report623(text,size,n,')
        code=code.replace(f'{k}=snprintf(text+n,size-(unsigned)n,','n=nes_report623(text,size,n,')
        code,n=re.subn(rf'if\({k}<0\|\|\(unsigned\){k}>=size-\(unsigned\)n\)return -1;\s*n\+={k};','if(n<0)return -1;',code)
        assert n==(2 if k=='used' else 1)
    path.write_bytes(code.encode())


def prepare(base, out, policy, shared=False):
    assert sha(base/'src/obj-nes-100/firmware.stm')=='16fc6b34dee561a121ce14e74c50fd879378b97f9bd49d7d31b42a356dfef9a0'
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    path=out/'src/nes_budget210.c'
    code=path.read_text()
    # No intervening print between the boot and plan diagnostic headings.
    start=code.index(' int boot=snprintf')
    end=code.index(' if(cause<0',start)
    boot,plan=code[start:end].split(' int cause=snprintf(text+n,size-(unsigned)n,\n')
    fmt1,args1=boot.split('",\n',1)
    fmt2,args2=plan.split('",\n',1)
    args1=args1[:args1.index(');')]
    code=code[:start]+fmt1.replace('int boot','int cause')+'"\n'+fmt2+'",\n'+args1+',\n'+args2+code[end:]
    path.write_bytes(code.encode())
    path=out/'src/nes_native_sink165.c'
    code=path.read_text()
    anchor=' if(op==24)op=2;'
    quiet='' if policy!='quiet' else '''   for(unsigned i=0;i<4;i++)
    if(!nes_cost474_pause(w->ctx,w->guard,0,false))return fail(s,5);
'''
    narrow='' if policy in ('drain','snapshots') else ''' &&
    (unsigned)(s->bg_next-2)<3 && s->obj_next && s->plan->bulk_valid &&
    s->plan->bulk[1]==1 && (unsigned)(s->plan->bulk[2]|s->plan->bulk[3]<<8)==32u*s->obj_next'''
    block=''' /* The original span still owns packet boundaries and compression. Wait
  * only on real outstanding credit. A consume ACK does not grant display. */
 if(section==3 && at==128 && s->plan && s->plan->window'''+narrow+'''){
  struct nes_sink_window184 *w=s->plan->window;
  if((uint16_t)(w->sent-w->retired)==2 && w->last[1]==3){
   uint8_t consumed[12];
   if(!nes_window184_drain(w,consumed))return fail(s,5);
'''+quiet+'''  }
 }
'''
    if policy=='small-snapshots':
        block=once(block,narrow,' && (unsigned)(s->bg_next-2)<3')
    if policy in ('snapshots','small-snapshots'):
        block=once(block,'   if(!nes_window184_drain','   for(unsigned sample=0;sample<4;sample++)\n    if(!nes_window184_drain')
    path.write_bytes(once(code,anchor,block+anchor).encode())
    if shared:share_report(out/'src')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','out'):
        p.add_argument(name,type=Path)
    p.add_argument('policy',choices=('drain','quiet','snapshots','small-snapshots'))
    p.add_argument('--shared-report',action='store_true')
    a=p.parse_args()
    prepare(a.base,a.out,a.policy,a.shared_report)
