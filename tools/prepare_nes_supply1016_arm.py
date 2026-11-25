"""Build the MMC1012 ARM schedule with targeted post-ACK readback for MMC1016."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from nes_display1010 import ROOT, once
from prepare_nes_tail1012 import WORK as BASE

WORK = BASE.with_name("nes-supply1016")
SRC = WORK/"link/src"

def prepare(refresh=False):
    prior=json.loads((ROOT/"analysis/trial1012-package.json").read_bytes())
    assert hashlib.sha256((BASE/"link/src/obj-nes-100/firmware.stm").read_bytes()).hexdigest()==prior["firmware"]
    if refresh:
        for name in ("VERSION","nes_menu_diagnostic.c","nes_checkpoint112.c","nes_native_sink165.c",
                     "nes_sink_window184.c","nes_frame900.h","nes_budget210.c"):
            shutil.copyfile(BASE/"link/src"/name,SRC/name)
    else:
        shutil.copytree(BASE/"link",WORK/"link",ignore=shutil.ignore_patterns("*.log"))
    for name in ("VERSION","nes_menu_diagnostic.c","nes_checkpoint112.c"):
        f=SRC/name
        f.write_bytes(f.read_bytes().replace(b"1012",b"1016"))
    # Remove only the previous diagnostic callbacks, retaining all flow control.
    for name,old,new in (("nes_native_sink165.c"," ready1012(b);\n",""),
                         ("nes_sink_window184.c"," if(delta)credit1012(r);\n",""),
                         ("nes_sink_window184.c"," issue1012(s->sent);\n",""),
                         ("nes_sink_window184.c"," sent1012();\n","")):
        f=SRC/name;f.write_text(once(f.read_text(),old,new),newline="\n")
    f=SRC/"nes_frame900.h";s=f.read_text()
    s=s[:s.index("struct packet1012")]+s[s.index("struct log900 {"):]
    s=once(s,"struct trace1012 trace[3];","uint16_t selected, page_count, attempts; uint8_t meta[32], words[2048];")
    f.write_text(s,newline="\n")
    f=SRC/"nes_budget210.c";s=f.read_text()
    s=s[:s.index("/* Only the validated FPGA header")]+s[s.index("static struct row900 *pending950;"):]
    a=s.index(" bool match=page905");b=s.index("\n}",a)
    s=s[:a]+""" struct log900 *log=log900p;
 if(!page905(h,128) || h[1]!=0xb6 || h[30]!=128 || h[31]!=0xa5 ||
    (h[2]|h[3]<<8)!=r->gen || (r->descriptor[0] && memcmp(h+4,r->descriptor+8,4)))return false;
 if(log->selected || r==&log->other || r->valid!=3 || r->tick<5900 || r->tick>=6000 ||
    r->bg!=521 || r->obj!=17 || r->dirty!=23 || (h[27]&7)!=3 ||
    memcmp(r->descriptor,"\\x01\\x01\\x40\\x00\\xe0\\x01",6))return true;
 ++log->attempts;
 log->page_count=0;
 memcpy(log->meta,h,32);
 uint8_t page[32] __attribute__((aligned(4)));
 unsigned tiles=0;
 for(unsigned i=0;i<128;++i){
  if(!page905(page,i) || memcmp(page+1,h+1,7) || memcmp(page+24,h+24,6) ||
     page[30]!=i || page[31]!=0xa5)return false;
  memcpy(log->words+i*16,page+8,16);
  ++log->page_count;
  for(unsigned j=8;j<24;j+=4){
   uint32_t word;
   memcpy(&word,page+j,4);
   if(word==0xff000000){
    if(tiles==15)log->selected=1+(r-log->rows);
    return true;
   }
   if(word==0xfe000000)return false;
   tiles+=(word>>28)==10;
   if((word>>16)==0xd000 && (uint16_t)word!=r->gen)return false;
  }
 }
 return false;"""+s[b:]
    s=once(s,"active1012=0;pending950","pending950").replace("edition=1012","edition=1016")
    f.write_text(s,newline="\n")

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh",action="store_true")
    prepare(parser.parse_args().refresh)
