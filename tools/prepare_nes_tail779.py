# SPDX-License-Identifier: MIT
"""Dispatch the immutable section after the final map enqueue, inside its idle wait."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from nes_raw506 import once, sha
from prepare_nes_prefix777 import prepare as section_first


def physical(base, out):
    """Keep the 763 client and checked emitter. Put the table between disjoint map runs."""
    path = base/"nes_native_sink165.c"
    assert sha(path)=="ce3274e72b2821fe4341c526e4e52bcef72262a9e4580ae2bb7d6102ed22b107"
    source=path.read_text()
    m=source.index(" if(!map527(s,p,r->map_upload,false))")
    a=source.index(" bool same=same635(s,p);",m)
    b=source.index(" if(!span(s,5,0,p->hdma",a)
    c=source.index(" uint8_t descriptor[168];",b)
    source=source[:a]+source[b:c]+" if(later779 && !map527(s,p,later779,false))return false;\n"+source[a:b]+source[c:]
    source=once(source," if(!map527(s,p,r->map_upload,false))return false;", """ uint64_t later779=0;
 if(p->patch_count && s->displayed && s->ack635[r->target] && s->ack635[1-r->target]){
  uint32_t high=(uint32_t)(r->map_upload>>32);
  uint32_t end=(high+(high&(0u-high))) & ~high;
  if(end)later779=(uint64_t)(high & (0u-end))<<32;
 }
 if(!map527(s,p,r->map_upload & ~later779,false))return false;""")
    out.mkdir(parents=True,exist_ok=False)
    (out/path.name).write_text(source,newline="\n")


def prepare(base, out, split):
    out.mkdir(parents=True, exist_ok=False)
    with TemporaryDirectory(dir=out) as tmp:
        source_dir = Path(tmp) / "source"
        section_first(base, source_dir, table_first=True)
        path = source_dir / "nes_native_sink165.c"
        source = path.read_text()
        a = source.index(" bool same=same635(s,p);")
        b = source.index(" /*719", a)
        source = source[:a] + """ bool early779=false;
 if(!map527(s,p,r->map_upload,false))return false;
""" + source[b:]
        source = once(source, "   unsigned left=w->poll_limit;", """   if(p->patch_count && s->displayed && s->ack635[r->target] &&
      s->ack635[1-r->target] && same635(s,p)){
    /* The map heads are queued. Section 5 has its own sequential cursor.
     * Its checked dispatcher still polls the tile producer before each E1. */
    if(!section777(s,p,&size[5]))return false;
    early779=true;
   }
   unsigned left=w->poll_limit;""")
        source = once(source, " if(same&&s->displayed", " bool same=early779||same635(s,p);\n if(same&&s->displayed")
        source = once(source, "!early777 && !section777", "!early779 && !section777")
        if split:
            # Protect the first run on page two and every earlier left-page row.
            # Split only at a clean gap in the prepared immutable upload mask.
            source = once(source, " if(!map527(s,p,r->map_upload,false))return false;",
                          """ uint64_t later779=0;
 if(p->patch_count && s->plan && s->plan->bank_history==2 &&
    s->displayed && s->ack635[r->target] && s->ack635[1-r->target] && same635(s,p)){
  uint32_t high=(uint32_t)(r->map_upload>>32);
  if(high){
   uint32_t first=high & (0u-high);
   uint32_t end=(high+first) & ~high;
   if(end)later779=(uint64_t)(high & (0u-end))<<32;
  }
 }
 if(!map527(s,p,r->map_upload & ~later779,false))return false;
 if(later779){
  if(!section777(s,p,&size[5]) || !map527(s,p,later779,false))return false;
  early779=true;
 }""")
            source=once(source, "   if(p->patch_count && s->displayed",
                                "   if(!early779 && p->patch_count && s->displayed")
        (out / path.name).write_text(source, newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--split",action="store_true")
    parser.add_argument("--physical",action="store_true")
    args = parser.parse_args()
    if args.physical:
        physical(args.base,args.out)
    else:
        prepare(args.base,args.out,args.split)
