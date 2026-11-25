"""Add a bounded, same-generation ARM packet trace to the routed MMC1010 board."""
import hashlib
import json
import shutil
from pathlib import Path

from nes_display1010 import ROOT, once
from prepare_nes_display1010_arm import PROBE

WORK = ROOT.parent / "probes/nes-tail1012-final"


def prepare():
    link = WORK/"link"
    baseline = json.loads((ROOT/"analysis/trial1010-package.json").read_bytes())
    assert hashlib.sha256((PROBE/"src/obj-nes-100/firmware.stm").read_bytes()).hexdigest() == baseline["firmware"]
    shutil.copytree(PROBE, link, ignore=shutil.ignore_patterns("*.log"))
    src = link/"src"
    def edit(name, *pairs):
        f = src/name
        s = f.read_text()
        for old, new in pairs:
            s = once(s, old, new)
        f.write_text(s, newline="\n")

    edit("nes_frame900.h", ("struct log900 {", """
struct packet1012 { uint8_t op, section; uint16_t offset, payload, ready, issue, sent, credit; };
struct trace1012 { uint32_t base; uint16_t gen, count, credits, first_sent, e0, tick;
 struct packet1012 packet[64]; };
void ready1012(const uint8_t *);
void issue1012(uint16_t);
void sent1012(void);
void credit1012(uint16_t);
struct log900 {"""), ("rows[124]; uint16_t displayed55;", "rows[80]; uint16_t displayed55; struct trace1012 trace[3]; struct row900 other;"))
    edit("nes_native_sink165.c", ('#include "nes_sink_window184.h"', '#include "nes_frame900.h"\n#include "nes_sink_window184.h"'),
         (" s->state=NES_SINK165_BUSY;"," ready1012(b);\n s->state=NES_SINK165_BUSY;"))
    edit("nes_sink_window184.c", (" s->retired=r;", " if(delta)credit1012(r);\n s->retired=r;"),
         (" if(!io(s,tx,tx,n+3))return false;", " issue1012(s->sent);\n if(!io(s,tx,tx,n+3))return false;\n sent1012();"))
    helper = (ROOT/"tools/nes_tail1012.inc").read_text()
    edit("nes_budget210.c", ("static struct row900 *pending950;", helper+"\nstatic struct row900 *pending950;"),
         (" return page905(h,0)", " bool match=page905(h,0)"),
         (" : !r->descriptor[0]);", " : !r->descriptor[0]);\n if(match)keep1012(r);\n return match;"),
         (" if(log->used>=log->capacity){++log->drop[w-1];return;}\n struct row900 *r=&log->rows[log->used++];",
          """ unsigned dirty=__builtin_popcountll(v->map_dirty);
 struct row900 *r=&log->other;
 if(dirty==23){
  if(log->used<log->capacity)r=&log->rows[log->used++];
  else ++log->drop[w-1];
 }"""),
         ("r->dirty=__builtin_popcountll(v->map_dirty);","r->dirty=dirty;"),
         (" pending950=NULL;latest900=0;", " active1012=0;pending950=NULL;latest900=0;"),
         ("edition=1010","edition=1012"), ("log900p->capacity=124","log900p->capacity=80"))
    for name in ("nes_menu_diagnostic.c", "nes_checkpoint112.c", "VERSION"):
        f = src/name
        f.write_bytes(f.read_bytes().replace(b"1010", b"1012"))


if __name__ == "__main__":
    prepare()
