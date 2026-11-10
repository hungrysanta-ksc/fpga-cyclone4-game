"""732B schedule, remove redundant zero-padding ROM storage and scan.

DATA2 with an internal NULL source denotes zero-filled bytes in the existing
initialized packet buffer. Wire ABI, odd lengths, packet boundaries and
independent receiver checks are unchanged. Other expanded opcodes retain
their non-NULL source checks.
"""
import argparse,json
from pathlib import Path
from types import SimpleNamespace
from prepare_nes_extent732 import run as extent
from nes_raw506 import once,sha

def run(a):
 extent(SimpleNamespace(base=a.base,out=a.out,cursor=True,shared_wait=False,direct=False))
 p=a.out/'nes_native_sink165.c';s=p.read_text()
 s=once(s,'if(op==2 && data && n>=4 && !(n&1)){\n  unsigned i=2;while(i<n && data[i]==data[i&1])i++;',
 '''/*733 A NULL internal DATA source uses the already zeroed packet buffer.
  * Preserve the identical-word compression and all odd-length DATA bytes. */
 if(op==2 && n>=4 && !(n&1)){
  unsigned i=n;
  if(data){i=2;while(i<n && data[i]==data[i&1])i++;}''')
 s=once(s,'put16(b+12,n);if(n)memcpy(b+16,data,n);','put16(b+12,n);if(n && data)memcpy(b+16,data,n);')
 s=once(s,'static const uint8_t zero[240]={0};','static const uint8_t zero[2]={0};')
 s=once(s,'else if(!packet(s,2,5,offset,zero,n))return false;',
              'else if(!packet(s,2,5,offset,NULL,n))return false;')
 p.write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe733.json')).write_text(json.dumps(dict(stage=733,base=sha(a.base/'obj-nes-100/firmware.stm'),source=sha(p),scope=__doc__,new_static_RAM_B=0,new_RTL=False,new_65816=False),indent=2)+'\n',encoding='utf8',newline='\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
