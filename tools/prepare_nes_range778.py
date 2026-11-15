# SPDX-License-Identifier: MIT
"""Refresh the checked credit at an adjacent, completed warm map offer."""
import argparse
from pathlib import Path
from nes_raw506 import once, sha


def prepare(base, out, copy_rows=False):
    path = base / "nes_native_runtime165.c"
    assert sha(path) == "c285b1b541b6c816b1e8ada77c8c26aa51ee7f0bfb95bac0ae20b0ec9c52a893"
    source = once(path.read_text(), "  if(!nes_plan527_map_credit", """  if(!final && s->sink.map_pair683 && s->plan.bank_history==2 &&
     (uint16_t)(s->transport.sent-s->transport.retired)>=3){
   if(!nes_window532_room(&s->transport,&ready))return false;
   if(!ready)return true;
  }
  if(!nes_plan527_map_credit""")
    out.mkdir(parents=True, exist_ok=False)
    (out / path.name).write_text(source, encoding="utf8", newline="\n")
    if copy_rows:
        path = base / "nes_planner211.c"
        assert sha(path) == "19ea92413c98e9702aa87fba9c8b4a4d83863a2978ee778dcbfef8112328d95e"
        source = once(path.read_text(), "   for(unsigned x=0;x<33;x++){", """   if(old_column==new_column && bank[g]==bank[reuse]){
    /* The checked 66-byte source row, palette and placement all match.
     * Reuse only the 33 visible words. The rest remain inherited. */
    unsigned col=new_column, remaining=33;
    while(remaining){
     unsigned count=32-(col&31);
     if(count>remaining)count=remaining;
     unsigned page=(col>>5)*2048+(col&31)*2;
     const uint8_t *from=p->map+page+reuse*64;
     uint8_t *to=p->map+page+g*64;
     if(memcmp(to,from,count*2)){
      memcpy(to,from,count*2);
      p->map_dirty|=UINT64_C(1)<<(g+(col&32));
     }
     remaining-=count;col=(col+count)&63;
    }
   }else for(unsigned x=0;x<33;x++){""")
        (out / path.name).write_text(source, encoding="utf8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--copy-rows", action="store_true")
    args = parser.parse_args()
    prepare(args.base, args.out, args.copy_rows)
