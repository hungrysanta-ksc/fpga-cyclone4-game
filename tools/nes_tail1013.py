"""Isolate early OAM reuse from early map emission on the MMC1012 link."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from nes_display1010 import ROOT, once
from prepare_nes_tail1012 import WORK as BASE

WORK = BASE.with_name("nes-tail1013")
VARIANTS = ("oam", "map")


def prepare(mode):
    manifest = json.loads((ROOT/"analysis/trial1012-package.json").read_bytes())
    original = BASE/"link"
    assert hashlib.sha256((original/"src/obj-nes-100/firmware.stm").read_bytes()).hexdigest() == manifest["firmware"]
    link = WORK/mode/"link"
    shutil.copytree(original, link, ignore=shutil.ignore_patterns("*.log"))
    f = link/"src/nes_native_sink165.c"
    body = f.read_text()
    if mode == "oam":
        body = once(body, " }else if(!r->map_upload && r->writes==1){",
                    " }else if((r->map_upload==0x7fffff && p->patch_count==1) || (!r->map_upload && r->writes==1)){")
        body = once(body, "With no map DMA to protect, retire the checked reuse head",
                    "In these two layouts, retire the checked reuse head")
    elif mode == "map":
        anchor = " p->scroll_issued=true;"
        body = once(body, anchor, anchor + """
 /* All BG slots and map rows are final when the scroll table exists.
  * Use the same checked queue and cursor as the ordinary map sender. */
 if(map==0x7fffff && (s->map_next&127)==12 && !map527(s,p,map,3))return false;
""".rstrip())
    else:
        raise ValueError(mode)
    f.write_text(body, newline="\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=VARIANTS)
    prepare(p.parse_args().mode)
