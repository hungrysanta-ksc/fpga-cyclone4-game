"""Build the diagnostic row-run exporter and its paired M4 receiver from pinned 577/600 sources."""
import argparse
import shutil
from pathlib import Path

from check_nes_wire600 import ROOT, pin, read
from nes_raw506 import once


def sources(board,probe,out,candidate):
    manifest=read(ROOT/'analysis/whole580-manifest.json')['FPGA_inputs']
    for name in ('nes_native_export203.sv','nes_native_mailbox165.sv'):
        pin(board/name,manifest[name]['sha256'])
        shutil.copyfile(board/name,out/name)
    spi='nes_native_spi165.sv'
    pin(probe/'shared'/spi,read(ROOT/'analysis/wire600-verification.json')['RTL']['shared'])
    shutil.copyfile(probe/'shared'/spi,out/spi)
    if not candidate:return
    f=out/spi
    f.write_bytes(once(f.read_text(),"pack_byte=8'h51","pack_byte=8'h52").encode())
    f=out/'nes_native_export203.sv'
    s=once(f.read_text(),"else if(query_kind==1||query_kind==5)\n     tx_data=", """else if(query_kind==1)
     tx_data={3'd6,generation,5'b11110,count_minus_one,56'd0,held_data[7:0]};
    else if(query_kind==5)
     tx_data=""")
    s=once(s,'end else if(query_kind==1||query_kind==5)begin',"""end else if(query_kind==1)begin
      // The first non-successor belongs to the next run. Re-query it after VALUE.
      if(data[63:8]!=0)fail(3);
      else if(pack_count==0 || {1'b0,data[7:0]}=={1'b0,held_data[7:0]}+pack_count)begin
       if(pack_count==0)held_data<=data;
       pack_count<=pack_count+1'b1;query_index<=query_index+1'b1;state<=ASK;
      end else state<=VALUE;
     end else if(query_kind==5)begin""")
    f.write_bytes(s.encode())


def firmware(probe,out):
    src=probe/'ARM'
    pin(src/'src/obj-nes-100/firmware.stm',read(ROOT/'analysis/wire600-verification.json')['ARM']['shared']['firmware_sha256'])
    shutil.copytree(src,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    f=out/'src/nes_native165.c'
    s=once(f.read_text(),'p[0]!=0x51','p[0]!=0x52')
    s=once(s,' if(kind==6 && (index&0x1f00)==0x1000){',''' if(kind==6 && (index&0x1f00)==0x1e00){
  unsigned count=(index&255)+1, start=s->at[1];
  /* The last row is also the maximum. Check before writing any tentative byte. */
  if(s->state!=NES_NATIVE165_RECEIVING || gen!=s->generation || s->next_kind>1 ||
     s->at[0]!=s->counts[0] || start+count>s->counts[1] ||
     v>255 || (unsigned)v+count>8u*(s->counts[0]/33u))return fail(s,33);
  for(unsigned i=0;i<count;i++)s->rows[start+i]=(uint8_t)(v+i);
  s->next_kind=1;s->at[1]=start+count;s->records+=count;return true;
 }
 if(kind==6 && (index&0x1f00)==0x1000){''')
    s=once(s,'if((k!=1&&k!=5)||n>8','if(k!=5||n>8')
    f.write_bytes(s.encode())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('probe',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();firmware(a.probe,a.out)
