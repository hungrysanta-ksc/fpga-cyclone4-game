"""Build the checked raster run on the 878 FINISH/EA ownership path."""
import argparse
from pathlib import Path

from check_nes_strip869 import digest
from nes_raw506 import once


def prepare(base,out):
    assert digest(base/'obj-nes-100/firmware.stm')=='a6289db01b8038a3738b8c7c16418748c3922cb35d06c90c22c46b632bdeab05'
    name='nes_native165.c'
    src=(base/name).read_text()
    marker='static bool record(struct nes_native165'
    leaf='''/* Header bounded the entire normal raster run. The first line passed
 * logical_record; raster_next471 changes only its low 15 address bits. */
static void __attribute__((noipa)) raster_tail879(struct nes_native165 *s,
 unsigned start,unsigned count,uint64_t first){
 for(unsigned i=1;i<count;i++){
  first=raster_next471(first);
  s->raster[start+i]=first;
 }
 s->at[4]+=count-1;
 s->records+=count-1;
}
'''
    src=once(src,marker,leaf+marker)
    old='''  for(unsigned i=0;i<n;i++){
   if(!logical_record(s,4,gen,start+i,v))return false;
   v=raster_next471(v);
  }'''
    src=once(src,old,'''  if(!logical_record(s,4,gen,start,v))return false;
  raster_tail879(s,start,n,v);''')
    out.mkdir(parents=True)
    (out/name).write_text(src,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    prepare(**vars(p.parse_args()))
