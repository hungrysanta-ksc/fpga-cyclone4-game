# SPDX-License-Identifier: MIT
"""Insert validated OBJ records by physical slot within the current E9 run."""
import argparse
import json
from pathlib import Path

from nes_raw506 import once, sha

ROOT = Path(__file__).resolve().parents[1]

INSERT = """unsigned at=p->bytes;
 if(q->kind==1){
  /* Valid OBJ slots fit one byte. Full OBJ records have no alternate tags. */
  at=p->obj_start;
  while(at<p->bytes){
   const uint8_t *prior=p->buffer+4+at;
   unsigned compact=prior[0]==0x81;
   if(prior[4-compact]>q->slot)break;
   at+=compact?8:16;
  }
  if(at!=p->bytes)memmove(p->buffer+4+at+n,p->buffer+4+at,p->bytes-at);
 }else p->obj_start=(uint8_t)(p->bytes+n);
 memcpy(p->buffer+4+at,encoded,n);"""


COMPACT_INSERT = """unsigned at=p->bytes;
 if(encoded[0]==0x81){
  /* The compact OBJ form has a fixed eight-byte record and a validated slot <128. */
  while(at>p->obj_start && p->buffer[4+at-8+3]>q->slot){
   memcpy(p->buffer+4+at,p->buffer+4+at-8,8);
   at-=8;
  }
 }else p->obj_start=(uint8_t)(p->bytes+n);
 memcpy(p->buffer+4+at,encoded,n);"""


def prepare(a):
    pin=json.loads((ROOT/"analysis/obj518-verification.json").read_text())["windows"]
    assert sha(a.arm/"obj-nes-100/firmware.stm")==pin["firmware_SHA256"]
    a.out.mkdir(parents=True,exist_ok=False)
    name="nes_plan_service200.h"
    header=once((a.arm/name).read_text(),"bool early,ending;","bool early,ending;uint8_t obj_start;")
    (a.out/name).write_text(header,newline="\n")
    name="nes_plan_service200.c"
    source=(a.arm/name).read_text()
    source=once(source,"p->sent++;p->bytes=0;p->count=0;", "p->sent++;p->bytes=0;p->count=0;p->obj_start=0;")
    source=once(source,"memcpy(p->buffer+4+p->bytes,encoded,n);",COMPACT_INSERT if a.compact else INSERT)
    (a.out/name).write_text(source,newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("arm","out"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--compact",action="store_true")
    prepare(p.parse_args())
