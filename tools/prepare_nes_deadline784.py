# SPDX-License-Identifier: MIT
"""Build ARM variants for the 953–954 display deadline from the exact 783G link."""
import argparse
from pathlib import Path
from nes_raw506 import once, sha


def prepare(base, out, mode):
    assert sha(base/"obj-nes-100/sd2snes.elf")=="e39c66995900e635da42b87567e84d51f73ba00cd0f1203b79447e72c315093f"
    out.mkdir(parents=True,exist_ok=False)
    if mode=="bgfirst":
        name="nes_native_runtime165.c"
        text=(base/name).read_text()
        # During BG-first planning, reserve the shared bus until the first
        # real E9 batch was sent. The row cursor is untouched on a deferral.
        text=once(text," return nes_sink527_early(&s->sink", """ if(!final && !s->plan.sent)return true;
 return nes_sink527_early(&s->sink""")
        (out/name).write_text(text,newline="\n")
    if mode=="both":
        name="nes_plan_service200.c"
        text=(base/name).read_text()
        old=""" if((uint16_t)(p->window->sent-p->window->retired)>=3 ||
    (p->bulk_pending && (uint16_t)(p->window->sent-p->bulk_until)>=3))return true;"""
        new=""" if(p->bulk_pending && (uint16_t)(p->window->sent-p->bulk_until)>=3)return true;
 /* A cached full window can outlive the SNES receipt. Refresh real credit
  * before declining this immutable row; the following E8 still owns bulk. */
 if(!nes_window532_room(p->window,ready))return false;
 if(!*ready)return true;"""
        (out/name).write_text(once(text,old,new),newline="\n")
    if mode in ("raw","both","overlap","bgfirst"):
        name="nes_native_sink165.c"
        text=(base/name).read_text()
        # span and the OAM planner previously compiled two copies of the
        # full RLE cost walk. A <=64-byte range always fits one DATA head
        # and cannot contain an interior 64-byte repeat saving a header.
        cost=text[text.index("static unsigned span_cost227"):text.index("static bool oam227")]
        text=text.replace(cost,"")
        cost=once(cost,"unsigned span_cost227(const uint8_t *b,unsigned n)","unsigned costs784(const uint8_t *b,unsigned n,bool *use_split)")
        cost=once(cost," return old<split?old:split;"," *use_split=split<old;return *use_split?split:old;")
        cost+="""static unsigned span_cost227(const uint8_t *b,unsigned n){
 bool split;
 return costs784(b,n,&split);
}
"""
        text=once(text,"static bool span(",cost+"static bool span(")
        lo=text.index(" unsigned oldcost=0,newcost=0;")
        hi=text.index(" /* Synchronous immutable",lo)
        text=text[:lo]+""" bool split=false;
 if(n>64)costs784(b,n,&split);
"""+text[hi:]
        text=once(text,"if(newcost<oldcost)","if(split)")
        if mode=="overlap":
            # A staged BG receipt can still be pending when the final dense
            # map has entered the FIFO. Let normal plan progress resolve that
            # identity and submit the OBJ before the map queue is fully empty.
            # FINAL still drives every bulk and SEAL through its checked ACK.
            text=once(text,"if(s->plan && s->plan->window && (((uint32_t)",
                      "if(s->plan && !s->plan->bulk_pending && s->plan->window && (((uint32_t)")
        (out/name).write_text(text,newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("base",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("mode",choices=("raw","both","overlap","bgfirst"))
    a=p.parse_args()
    prepare(a.base,a.out,a.mode)
