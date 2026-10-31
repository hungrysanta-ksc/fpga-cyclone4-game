# SPDX-License-Identifier: MIT
"""Publish row receipts at final ACK and accept omitted runs of verified zero map words."""
import argparse
import json
from pathlib import Path
import nes_trim514 as trim
from nes_raw506 import once, sha

# 1460..146f = two published 64-row receipt bitmaps; 1470..1473 = serial low.
# BEGIN already checks the full serial/display base, generation, epoch and bank.
PUBLISH = """
 c.emit(0x8a,0x0a,0xaa);lda(0x1222);c.absolute(0x9d,0x1470)
 c.emit(0x8a,0x0a,0x0a,0xaa)
 for offset in range(0,8,2):
  lda(0x1310+offset);c.absolute(0x9d,0x1460+offset)
  c.emit(0x49,255,255);c.absolute(0x9d,0x1480+offset)
 c.absolute(0xae,0x1034)
"""

def client(out):
    check=trim.CHECK[:trim.CHECK.index(' imm(65535)')]
    check+="""
 lda(0x1034);c.emit(0x0a,0xaa);c.absolute(0xbd,0x1470);cmp(0x120e);cond(0xd0,'bad_packet')
"""
    spans=trim.CHECK[trim.CHECK.index(' lda(0x62);c.emit(0x38)'):trim.CHECK.index(' lda(0x1262);cmp(0x120e)')]
    check+=spans+trim.CHECK[trim.CHECK.index(" call(c,'service')"):trim.CHECK.index(" c.label('edge_span514')")]
    check+="""
 c.label('edge_span514');c.emit(0xc0,0,0);c.branch(0xf0,'edge_return515')
 c.emit(0x48,0x5a)
 for _ in range(6):c.emit(0x4a)
 c.emit(0x48,0x29,7,0,0xa8);imm(1)
 c.label('receipt_mask515');c.emit(0xc0,0,0);c.branch(0xf0,'receipt_test515')
 c.emit(0x0a,0x88);c.branch(0x80,'receipt_mask515')
 c.label('receipt_test515');sta(0x1262);c.emit(0x68,0x4a,0x4a,0x4a,0xaa)
 lda(0x1034);c.branch(0xf0,'bank_zero515');c.emit(0x8a,0x18,0x69,8,0,0xaa)
 c.label('bank_zero515');c.absolute(0xbd,0x1460);c.absolute(0x2d,0x1262);cond(0xf0,'bad_packet')
 c.absolute(0xbd,0x1480);c.absolute(0x2d,0x1262);cond(0xd0,'bad_packet')
 c.emit(0x7a,0x98,0x4a,0x4a,0x4a,0xa8,0x68)
 c.emit(0x18);c.absolute(0x6d,0x1020);c.emit(0x18,0x69,0,0x50,0xaa)
 c.label('edge_byte514');c.long(0xbf,0x7f0000)
 for offset in (2,4,6):c.long(0x1f,0x7f0000+offset)
 cond(0xd0,'bad_packet')
 c.emit(0x8a,0x18,0x69,8,0,0xaa,0x88);c.branch(0xd0,'edge_byte514')
 c.label('edge_return515');c.emit(0x60)
"""
    return trim.client(out,check=check,publish=PUBLISH,opcode=11)

EDGE = """
static unsigned zero_edge515(const uint8_t *p,int step,unsigned limit){
 unsigned n=0;
 while(n<limit){
  uint32_t words[2];
  memcpy(words,p,sizeof words);
  if(words[0]|words[1])break;
  n+=8;
  if(n<limit)p+=step;
 }
 return n;
}
"""

def prepare(arm,out):
    trim.prepare(arm,out,build_client=client)
    patch=out/'patch'
    def change(name,old,new):
        p=patch/name
        p.write_text(once(p.read_text(),old,new),encoding='utf8',newline='\n')
    change('nes_resident211.h','uint8_t map_groups[2][64];','uint8_t map_groups[2][64],published_rows[2][8];')
    change('nes_resident211.c','memset(s->map_groups[bank],0,64);',"""
 for(unsigned i=0;i<8;i++){
  unsigned mask=0;
  for(unsigned bit=0;bit<8;bit++)if(s->map_groups[bank][i*8+bit])mask|=1u<<bit;
  s->published_rows[bank][i]=(uint8_t)mask;
 }
 memset(s->map_groups[bank],0,64);""")
    # Reset clears the struct; abort/epoch discard both publication namespaces.
    p=patch/'nes_resident211.c'
    s=p.read_text().replace('memset(s->map_groups,255,sizeof s->map_groups);',
               'memset(s->published_rows,0,sizeof s->published_rows);memset(s->map_groups,255,sizeof s->map_groups);')
    p.write_text(s,encoding='utf8',newline='\n')
    change('nes_native_sink165.c','extern uint16_t nes_crcpart514(uint16_t,const uint8_t *,unsigned);',EDGE)
    change('nes_native_sink165.c','  if(left+right && repeat_bytes(data,n)!=n){',"""
  const uint8_t *rows=r->published_rows[r->target];
  left=(rows[first>>3]&(1u<<(first&7)))?zero_edge515(data,8,left):0;
  unsigned last=g-1;
  right=(rows[last>>3]&(1u<<(last&7)))?zero_edge515(data+n-8,-8,right):0;
  if(left+right && repeat_bytes(data,n)!=n){""")
    change('nes_native_sink165.c',"""   uint16_t crc=nes_crcpart514(65535,data,left);
   crc=nes_crcpart514(crc,data+n-right,right);
   if(!packet_wire(s,10,2,at+left,data+left,n-left-right,crc))return false;""",
           """   if(!packet_wire(s,11,2,at+left,data+left,n-left-right,(uint16_t)(r->serial-2)))return false;""")
    change('nes_native_sink165.c','op!=10&&expanded','op!=11&&expanded')
    change('nes_native_sink165.c','b[0]==10||bulk_submit','b[0]==11||bulk_submit')
    change('nes_sink_window184.c','p[0]!=10&&p[0]!=7','p[0]!=11&&p[0]!=7')
    (out/'pins.json').write_text(json.dumps({p.name:sha(p) for p in patch.iterdir()},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('arm','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prepare(a.arm,a.out)
