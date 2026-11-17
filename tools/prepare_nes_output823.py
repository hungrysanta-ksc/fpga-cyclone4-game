"""Build map-before-ordinary candidates from the fitted 822 cache and 822B ARM."""
from pathlib import Path
import argparse
import shutil

from prepare_nes_mask820 import WORK, edit


def prepare(variant):
    root = WORK.parent / "nes-output823" / ("patch-" + variant)
    parents={"wide":"", "ordered":"wide", "ready":"wide","page":"wide","overlap":"wide",
             "flush":"ordered","pages":"page","select":"flush","wire":"flush","prefix":"flush","lend":"flush"}
    parent=parents.get(variant)
    if parent and not (root.parent/("patch-"+parent)).is_dir():
        prepare(parent)
    root.mkdir(parents=True)
    sink = root / "nes_native_sink165.c"
    if variant=="lend":
        for path in (root.parent/"patch-flush").iterdir():
            shutil.copyfile(path,root/path.name)
        # A compact OAM frame has its last map enqueued immediately before
        # scroll. Let the 65816 claim that range while its queue is empty.
        edit(sink,"   return true;\n  }\n }\n if(!(n&1))", """   return true;
  }
  if(s->plan->window){
   uint8_t ack[12];
   for(unsigned sample=0;sample<16;sample++){
    if(!nes_window184_drain(s->plan->window,ack))return fail(s,5);
    if(s->plan->window->status_flags&8)break;
   }
  }
 }
 if(!(n&1))""")
        return
    if variant=="prefix":
        for path in (root.parent/"patch-flush").iterdir():
            shutil.copyfile(path,root/path.name)
        # When the small OAM update fits the compact command, put the
        # immutable scroll head before the map, leaving its last credit idle.
        start=sink.read_text().index(" if(!s->plan->bulk_pending && (((uint32_t)(map>>32))")
        body=sink.read_text()
        end=body.index(" p->scroll_issued=true;\n return true;",start)
        sink.write_text(body[:start]+""" bool long_map=!s->plan->bulk_pending && (((uint32_t)(map>>32))&0x7ffffu)==0x7ffffu;
 if(!(n&1))p->hdma[n++]=0;
 if(long_map && fragments>112/4){
  p->hdma_size=n;
  return map527(s,p,map,3);
 }
 if(!packet(s,24,5,0,p->hdma,n) ||
    !packet_wire(s,25,5,n,zero,2,1121-n))return false;
 p->scroll_issued=true;
 return !long_map || map527(s,p,map,3);"""+body[end+len(" p->scroll_issued=true;\n return true;"):])
        return
    if variant=="wire":
        for path in (root.parent/"patch-flush").iterdir():
            shutil.copyfile(path,root/path.name)
        # Every header field is assigned before enqueue. Initialize only the
        # bytes actually put on the wire, including an implicit zero payload.
        edit(sink,"uint8_t b[256]={0},ack[12]={0};","uint8_t b[256],ack[12]={0};")
        edit(sink,"if(n && data)memcpy(b+16,data,n);",
             "if(n){if(data)memcpy(b+16,data,n);else memset(b+16,0,n);}")
        return
    if variant=="select":
        for path in (root.parent/"patch-flush").iterdir():
            shutil.copyfile(path,root/path.name)
        # The compact OAM head does not need the long map reservation. Keep
        # its original queue order, so the short OBJ can share the upload VB.
        edit(sink,"if(!s->plan->bulk_pending && (((uint32_t)(map>>32))","if(fragments>112/4 && !s->plan->bulk_pending && (((uint32_t)(map>>32))")
        body=sink.read_text()
        before="""  if(fragments>112/4){
   if(!(n&1))p->hdma[p->hdma_size++]=0;
   return true;
  }"""
        assert body.count(before)==1
        sink.write_text(body.replace(before,"  if(!(n&1))p->hdma[p->hdma_size++]=0;\n  return true;"))
        return
    if variant=="pages":
        for path in (root.parent/"patch-page").iterdir():
            shutil.copyfile(path,root/path.name)
        edit(sink,"if(!s->plan->bulk_pending && (((uint32_t)(map>>32))","if(fragments>112/4 && !s->plan->bulk_pending && (((uint32_t)(map>>32))")
        edit(sink,"  if(!nes_plan527_map_credit(s->plan,&ready))return false;","""  if(p->right_first && !s->plan->bulk_pending){
   if(!nes_window532_room(s->plan->window,&ready))return false;
   if(!ready)return true;
  }else if(!nes_plan527_map_credit(s->plan,&ready))return false;""")
        # Both formatting routines accept a negative incoming cursor and
        # reject it before touching the output buffer.
        budget=root/"nes_budget210.c"
        shutil.copyfile(WORK/"link820b/src"/budget.name,budget)
        body=budget.read_text()
        body=body.replace("if(n<0 || (unsigned)n>=size || len>(size-(unsigned)n-1)/2 || size-(unsigned)n<2*len+2)",
                          "if(n<0 || (unsigned)n>=size || size-(unsigned)n<2 || len>(size-(unsigned)n-2)/2)")
        body=body.replace(" if(n<0)return -1;\n n=nes_hexline512", " n=nes_hexline512")
        body=body.replace("20);if(n<0)return -1;\n n=nes_report623","20);\n n=nes_report623")
        budget.write_text(body)
        return
    if variant=="flush":
        for path in (root.parent/"patch-ordered").iterdir():
            shutil.copyfile(path,root/path.name)
        # Upload and retire the fragmented OBJ descriptors during the inherited
        # map's display wait. Only the full ordinary path takes this fence.
        edit(sink,"if(!p->scroll_issued && s->plan && s->plan->window && s->plan->window->last[1]==2 &&",
             "if(!p->scroll_issued && !p->map_dirty && s->plan && s->plan->window &&")
        edit(sink,"  for(unsigned poll=0;poll<120;poll++){", "  if(!nes_plan200_progress(s->plan,NES_FINAL553))return fail(s,5);\n  for(unsigned poll=0;poll<120;poll++){")
        return
    if variant in ("ordered","ready","overlap","page"):
        for path in (root.parent/"patch-wide").iterdir():
            shutil.copyfile(path,root/path.name)
        menu=root/"nes_menu_diagnostic.c"
        shutil.copyfile(WORK/"link820b/src"/menu.name,menu)
        edit(menu,"  used=nes_report594(text+n",'''  static const char labels[]="A|\\0B|\\0SELECT|\\0START|\\0UP|\\0DOWN|\\0LEFT|\\0RIGHT|";
  char names[sizeof labels];char *dst=names;
  const char *label=labels;
  for(unsigned mask=1;mask<=128;mask*=2){
   while(*label){if(b&mask)*dst++=*label;label++;}
   label++;
  }
  *dst=0;
  used=nes_report594(text+n''')
        edit(menu,r"buttons=\224\224\224\012",r"buttons=%s\012")
        edit(menu,'b?"":"NONE",b&1?"A|":"",b&2?"B|":"",b&4?"SELECT|":"",b&8?"START|":"",b&16?"UP|":"",b&32?"DOWN|":"",b&64?"LEFT|":"",b&128?"RIGHT|":""','b?names:"NONE"')
        # Any new E1 clears the idle-DMA notification. Polling a later OBJ's
        # retired identity cannot recover an earlier map's notification.
        edit(sink,"if(p->objects>112/4 && s->plan && s->plan->window &&",
             "if(!p->scroll_issued && s->plan && s->plan->window && s->plan->window->last[1]==2 &&")
        extra="" if variant in ("ordered","page") else """   uint8_t ack[12];struct nes_sink_window184 *w=s->plan->window;
   for(unsigned i=0;i<120;i++){
    if(!nes_window184_drain(w,ack))return fail(s,5);
    if(w->status_flags&8)break;
   }
"""
        if variant=="overlap":
            # Let the ARM build OBJ and issue E9 while the 65816 is free to DMA
            # the map. Fence only the first E1 that would take its queue head.
            edit(root/"nes_native_sink165.h","bool map_pair683;","bool map_pair683,map_wait;")
            edit(sink,"s->map_next=0;s->map_pair683=false;","s->map_next=0;s->map_pair683=false;s->map_wait=false;")
            edit(sink," if(s->plan && op>=2", " if(s->map_wait){\n  s->map_wait=false;\n"+extra+" }\n if(s->plan && op>=2")
            extra="   s->map_wait=true;\n"
        edit(sink,"if(fragments>112/4)return true;", """if(fragments>112/4){
   if(!(n&1))p->hdma[p->hdma_size++]=0;
"""+extra+"""   return true;
  }""")
        if variant=="page":
            base=WORK/"link820b/src"
            for name in ("nes_planner211.c","nes_native_video165.h"):
                shutil.copyfile(base/name,root/name)
            planner=root/"nes_planner211.c"
            edit(root/"nes_native_video165.h","bool scroll_issued;","bool scroll_issued,right_first;")
            edit(planner," unsigned next_offer=3;",""" p->right_first=inherit && s->counts[2]>112/4 &&
    (((uint32_t)(resident->map_stale[resident->target]>>32))&0x7ffffu)==0x7ffffu;
 unsigned next_offer=3;""")
            edit(planner,"(UINT64_C(1)<<(g-3))","(UINT64_C(1)<<((g-3)+(p->right_first?32:0)))")
            # At entry only the first 19 right rows are known to be owed.
            # Early offers cover complete triples entirely inside that prefix.
            edit(planner,"g>=next_offer &&","g>=next_offer && (!p->right_first || g<=18) &&")
            edit(sink," bool pairable=early!=1"," if(p->right_first)mask=(mask>>32)|(mask<<32);\n bool pairable=early!=1")
            edit(sink,"count<3&&((mask>>g)&1)","count<3&&(!p->right_first || g!=32)&&((mask>>g)&1)")
            edit(sink,"  bool adjacent=pair","  if(p->right_first)first^=32;\n  bool adjacent=pair")
        return
    shutil.copyfile(WORK.parent / "nes-output822/patch-b" / sink.name, sink)
    if variant in ("credit","combined","rows","wide"):
        # Full palette/OAM traffic lasts much longer than the acknowledged
        # compact OAM command. Only full traffic yields its queue slots.
        body = sink.read_text()
        start = body.index(" /* Allow a long accepted map tail")
        end = body.index("  /* Canonical raw CHR", start)
        body = body[:start] + body[end:]
        start = body.index(" if(!span(s,3,0,p->cgram,512))")
        end = body.index(" if(!oam227", start)
        sink.write_text(body[:start] + """ if(s->plan && s->plan->window && s->plan->bank_history==2 &&
    (((uint32_t)(r->map_upload>>32))&0x7ffffu)==0x7ffffu){
  uint8_t ack[12];
  struct nes_sink_window184 *w=s->plan->window;
  for(unsigned poll=0;poll<120;poll++){
   if(!nes_window184_drain(w,ack))return fail(s,5);
   if(w->status_flags&8)break;
  }
 }
 if(!span(s,3,0,p->cgram,512))return false;
""" + body[end:])
    if variant in ("map","combined","rows","wide"):
        # Mode 3 is entered only by the planner once all BG slots and map
        # bytes are final. The ordinary enqueue still validates each credit.
        edit(sink,"(early==1||adjacent)?24:2","(early==1||early==3||adjacent)?24:2")
        edit(sink,"if(early){s->map_next=", "if(early==3){s->map_next=(uint8_t)g;continue;}\n  if(early){s->map_next=")
        edit(sink," if(!(n&1))p->hdma[n++]=0;", """ if((((uint32_t)(map>>32))&0x7ffffu)==0x7ffffu){
  if(!map527(s,p,map,3))return false;
 }
 if(!(n&1))p->hdma[n++]=0;""")
        # No more than three later submissions may overtake a bulk receipt.
        # A pre-OBJ run with a pending descriptor stays on the normal path.
        if variant!="map":
            edit(sink,"if((((uint32_t)(map>>32))","if(!s->plan->bulk_pending && (((uint32_t)(map>>32))")
    if variant=="wide":
        base=WORK/"link820b/src"
        runtime=root/"nes_native_runtime165.c"
        header=root/"nes_native_sink165.h"
        for path in (runtime,header):
            shutil.copyfile(base/path.name,path)
        edit(header,"bool nes_scroll810(struct nes_native_sink165 *,struct nes_native_video165 *,uint64_t);","bool nes_scroll810(struct nes_native_sink165 *,struct nes_native_video165 *,uint64_t,unsigned);")
        edit(runtime,"s->video->map_dirty);","s->video->map_dirty,s->receiver->counts[2]);")
        edit(sink,"*p,uint64_t map){","*p,uint64_t map,unsigned fragments){")
        # The first 112 OAM bytes have their own compact command. Beyond that
        # head the immutable source can require a full ordinary transfer.
        # This is a scheduling hint; the actual independent comparisons remain.
        edit(sink,"if(!map527(s,p,map,3))return false;","if(!map527(s,p,map,3))return false;\n  if(fragments>112/4)return true;")
        edit(sink,"if(s->plan && s->plan->window && s->plan->bank_history==2 &&","if(p->objects>112/4 && s->plan && s->plan->window && s->plan->bank_history==2 &&")
    if variant=="rows":
        base=WORK/"link820b/src"
        for name in ("nes_resident211.h","nes_native_video165.h","nes_planner211.c","nes_native_runtime165.c"):
            shutil.copyfile(base/name,root/name)
        edit(root/"nes_resident211.h","(*offer_map)(void *,bool)","(*offer_map)(void *,unsigned)")
        edit(root/"nes_native_video165.h","bool scroll_issued;","bool scroll_issued;uint8_t right_sent;")
        edit(root/"nes_planner211.c","  nes_cost474_groups++;","""  /* complete groups never receive later map writes on either page */
  if(g>=p->right_sent+3u && resident->offer_map &&
     (((uint32_t)(resident->map_stale[resident->target]>>32)>>p->right_sent)&7u)==7u &&
     !resident->offer_map(resident->ctx,2))return fail(p,7);
  nes_cost474_groups++;""")
        edit(root/"nes_native_runtime165.c","offer527(void *ctx,bool final)","offer527(void *ctx,unsigned final)")
        edit(root/"nes_native_runtime165.c"," return nes_sink527_early"," if(final==2)return map527(&s->sink,s->video,0,4);\n return nes_sink527_early")
        edit(sink," bool pairable=early!=1",""" if(early==4){
  bool room;
  if(s->plan->bank_history!=2 || (s->map_next&127)>32 || s->plan->bulk_pending)return true;
  if(!nes_window532_room(s->plan->window,&room))return false;
  if(!room)return true;
  if(!nes_plan527_map_credit(s->plan,&room))return false;
  if(!room)return true;
  unsigned offset=2048+64*p->right_sent;
  if(!packet(s,24,2,offset,p->map+offset,192))return false;
  p->right_sent+=3;
  return true;
 }
 mask&=~((uint64_t)((1u<<p->right_sent)-1u)<<32);
 bool pairable=early!=1""")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("variant", choices=("credit","map","combined","rows","wide","ordered","ready","overlap","page","flush","pages","select","wire","prefix","lend"))
    prepare(parser.parse_args().variant)
