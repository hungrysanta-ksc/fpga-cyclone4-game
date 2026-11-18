"""Schedule the immutable scroll and fill at the long warm map boundary."""
import argparse
import shutil

from prepare_nes_mask820 import edit
from prepare_nes_trial802 import PROBES


def prepare(mode):
    source = PROBES / "nes-output823/link-826/src/nes_native_sink165.c"
    out = PROBES / "nes-demo827" / ("patch-" + mode)
    out.mkdir(parents=True,exist_ok=True)
    if mode=="obj":
        plan = out / "nes_plan_service200.c"
        shutil.copyfile(source.with_name(plan.name),plan)
        edit(plan,"while(cut && records[cut*8+3]==records[(cut-1)*8+3]+1)cut--;",
             """while(cut && records[cut*8+3]==records[(cut-1)*8+3]+1)cut--;
  if(cut>7){
   cut=4;
   while(cut<15 && records[cut*8+3]==records[(cut-1)*8+3]+1)cut++;
  }""")
        return
    sink = out / source.name
    sink.write_text(source.read_text(),newline="\n")
    if mode=="credit":
        # A checked END and the normal per-packet credit still apply. A DMA
        # progress notification is a scheduling hint, not a receipt.
        old=sink.read_text()
        start=old.index("  uint8_t ack[12];",old.index(" if(!p->scroll_issued && !p->map_dirty"))
        end=old.index("\n }\n if(!span(s,3",start)
        sink.write_text(old[:start]+"  if(!nes_plan200_progress(s->plan,NES_FINAL553))return fail(s,5);"+old[end:],newline="\n")
        return
    if mode=="fill":
        # Move only the short scroll and its bounded fill into the period
        # where the OBJ queue still owns work. Keep raw/table and SEAL last.
        at=sink.read_text().index(" if(!p->scroll_issued && !span(s,5")
        old=sink.read_text()
        end=old.index("  /* Read the enclosing object",at)
        original=old[at:end]
        helper=original[:original.index(" if(p->patch_count){")]
        fill=original[original.index("  while(offset<1121)"):].strip()
        helper+=" if(p->patch_count && !p->scroll_issued){\n  unsigned offset=p->hdma_size;\n  "+fill+"\n }\n return true;\n}\n"
        old=old[:at]+""" if(!early_fill && !scroll827(s,p))return false;
 if(p->patch_count){
  unsigned offset=1121;
"""+old[end:]
        old=old.replace(" bool same=same635(s,p);",""" bool early_fill=p->map_dirty && s->plan && s->plan->bank_history==2 &&
    (((uint32_t)(r->map_upload>>32))&0x7ffffu)==0x7ffffu;
 if(early_fill && !scroll827(s,p))return false;
 bool same=same635(s,p);""")
        old=old.replace("bool nes_sink212_seal(", "static bool scroll827(struct nes_native_sink165 *s,struct nes_native_video165 *p){\n"+helper+"bool nes_sink212_seal(")
        sink.write_text(old,newline="\n")
        return
    if mode=="pipeline":
        # bit 6 is already the terminal map cursor. Use a separate boolean
        # in existing alignment padding so map_next keeps its normal ABI.
        header=source.with_suffix(".h")
        (out/header.name).write_text(header.read_text().replace(
            "bool map_pair683;", "bool map_pair683, map_after_obj;"),newline="\n")
        edit(sink,"s->sequence=0;s->bg_next", "s->map_after_obj=false;s->sequence=0;s->bg_next")
        edit(sink,"  if(!map527(s,p,map,3))return false;\n  if(fragments>112/4){",
             "  if(fragments>112/4){\n   s->map_after_obj=true;")
        edit(sink,"   return true;\n  }\n }\n if(!(n&1))",
             "   return true;\n  }\n  if(!map527(s,p,map,3))return false;\n }\n if(!(n&1))")
        rt=source.with_name("nes_native_runtime165.c")
        dest=out/rt.name
        dest.write_text(rt.read_text(),newline="\n")
        edit(dest," nes_budget210_plan(q);return true;", """ if(s->sink.map_after_obj && q->kind==1 && s->plan.sent>1 && !s->plan.bulk_pending){
  s->sink.map_after_obj=false;
  if(!map527(&s->sink,s->video,s->resident->map_stale[bank]|s->video->map_dirty,3))return false;
 }
 nes_budget210_plan(q);return true;""")
        return
    if mode in ("overlap","inherited"):
        condition="fragments>112/4" if mode=="overlap" else "!p->map_dirty && fragments>112/4"
        edit(sink,"if(!map527(s,p,map,3))return false;",
             """/* Publish the first half now. Let the OBJ planner start E9
    * before servicing the suffix through the checked ordinary map path. */
  uint64_t ready=CONDITION ? map & ((UINT64_C(1)<<44)-1) : map;
  if(!map527(s,p,ready,3))return false;""".replace("CONDITION",condition))
        return
    if mode=="tail":
        # Overlap the expensive section-5 expansion with outstanding OBJ
        # receipts. All ordinary sends conduct the normal plan/credit service.
        begin=sink.read_text().index(" bool same=same635(s,p);")
        end=sink.read_text().index(" if(!p->scroll_issued && !span",begin)
        old=sink.read_text()
        ordinary=old[begin:end]
        insertion=old.index(" uint8_t descriptor[168]",end)
        sink.write_text(old[:begin]+old[end:insertion]+ordinary+old[insertion:],newline="\n")
        return
    original = """ if((((uint32_t)(map>>32))&0x7ffffu)==0x7ffffu){
  if(!map527(s,p,map,3))return false;
  if(fragments>112/4){
   if(!(n&1))p->hdma[p->hdma_size++]=0;
   return true;
  }
 }
"""
    # Both submissions still follow the checked bulk_pending guard. No saved
    # pointer crosses the OBJ planner's scratch reuse or the queue boundary.
    edit(sink, original, """ bool long_map=(((uint32_t)(map>>32))&0x7ffffu)==0x7ffffu;
 bool prefix_first=long_map && fragments>112/4;
 if(long_map && !prefix_first && !map527(s,p,map,3))return false;
""" if mode=="prefix" else """ if((((uint32_t)(map>>32))&0x7ffffu)==0x7ffffu && !map527(s,p,map,3))return false;
""")
    if mode=="prefix":
        edit(sink," p->scroll_issued=true;\n return true;",
             " p->scroll_issued=true;\n return !prefix_first || map527(s,p,map,3);")
    # Preserve the original extent for the SEAL size and independent check
    # when moving the padded prefix previously issued by the ordinary path.
    edit(sink," if(!(n&1))p->hdma[n++]=0;",
         " if(!(n&1)){p->hdma[n++]=0;if(fragments>112/4 && (((uint32_t)(map>>32))&0x7ffffu)==0x7ffffu)p->hdma_size=n;}")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("prefix","suffix","obj","overlap","tail","pipeline","fill","credit","inherited"))
    prepare(parser.parse_args().mode)
