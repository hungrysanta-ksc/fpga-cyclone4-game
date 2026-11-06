"""MMC643 table serialization and checked FIFO ordering for the final SEAL."""
import argparse
import shutil
from pathlib import Path
from check_nes_fault641 import digest, evidence
from nes_raw506 import once


def prepare(base,out):
    assert digest(base/"src/obj-nes-100/firmware.stm")==evidence("reject643-package.json")["firmware_SHA256"]
    shutil.copytree(base,out,ignore=shutil.ignore_patterns("obj-*",".dep-*","*.log"))
    path=out/"src/nes_native_sink165.c"
    source=path.read_text()
    start=source.index("  if(!span(s,5,offset,tables,243))")
    end=source.index("\n }",start)
    source=source[:start]+"""  /* The three tables have a fixed 243-byte wire layout. Pack their last
   * three bytes with the lengths, excluding C alignment padding. */
  if(!packet(s,2,5,offset,tables,240))return false;
  uint8_t tail[9];memcpy(tail,tables+240,3);
  memcpy(tail+3,p->patch.size,6); /* Three little-endian uint16_t on Cortex-M4. */
  if(!packet(s,2,5,offset+240,tail,sizeof tail))return false;
  size[5]=(uint16_t)(offset+249);"""+source[end:]
    path.write_text(source,newline="\n")
    path=out/"src/nes_sink_window184.c"
    path.write_text(once(path.read_text(),"if(s->ever_sent && !nes_window184_drain(s,ack))",
          """/* Each preceding head must retire at the FPGA identity/status checker.
  * A section-5 tail may precede SEAL in FIFO order. The post-send barrier
  * still requires the complete final display ACK; guard and credit run in send. */
 if(s->ever_sent && (p[0]!=3 || s->last[1]!=5) && !nes_window184_drain(s,ack))"""),newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("base",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    prepare(a.base,a.out)
