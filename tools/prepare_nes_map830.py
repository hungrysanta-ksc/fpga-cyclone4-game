"""Offer completed, newly dirty right-page rows during the BG planner."""
import argparse
from nes_raw506 import once
from nes_report828 import reports
from prepare_nes_map828 import PROBES


def prepare(mode):
    src = PROBES/"nes-output823/link-826/src"
    out = PROBES/"nes-map830"/("patch-"+mode)
    out.mkdir(parents=True,exist_ok=True)
    reports(src,out)
    if mode=="control":
        return
    def rewrite(name,changes):
        base=(PROBES/"nes-demo827/patch-fill"/name if mode=="grantfill" and name=="nes_native_sink165.c" else src/name)
        text=base.read_text()
        for old,new in changes:
            text=once(text,old,new)
        (out/name).write_text(text,newline="\n")
    if mode in ("complete","completefill","completeraw","joined","joinedfill","rawfill","rawfirst"):
        rewrite("nes_resident211.h",[("(*offer_map)(void *,bool)","(*offer_map)(void *,unsigned)")])
        rewrite("nes_planner211.c",[(" } /* compact groups */",""" } /* compact groups */
 /* At this point every slot and row is final. A mixed/cold map stays on
  * the normal path. Leave the scroll builder and all of its checks intact. */
 if(inherit && s->counts[2]>112/4 && p->patch_count && p->map_dirty &&
    resident->offer_map && !resident->offer_map(resident->ctx,2))return fail(p,7);""")])
        rewrite("nes_native_runtime165.c",[("offer527(void *ctx,bool final)","offer527(void *ctx,unsigned final)"),
            (" return nes_sink527_early",""" if(final==2){
  uint64_t map=s->resident->map_stale[s->resident->target]|s->video->map_dirty;
  if((uint32_t)map || (((uint32_t)(map>>32))&0x7ffffu)!=0x7ffffu ||
     s->plan.bank_history!=2 || s->plan.bulk_pending)return true;
  return map527(&s->sink,s->video,map,3);
 }
 return nes_sink527_early""")])
        if mode in ("completefill","joinedfill","rawfill"):
            source=PROBES/"nes-demo827/patch-fill/nes_native_sink165.c"
            (out/source.name).write_bytes(source.read_bytes())
        if mode in ("completeraw","rawfill","joined","joinedfill","rawfirst"):
            name="nes_native_sink165.c"
            source=out/name if (out/name).exists() and mode in ("rawfill","joinedfill") else src/name
            text=source.read_text()
            if mode in ("completeraw","rawfill"):
                text=once(text,"if(!span(s,5,offset,raw,packed))return false;","""if(p->objects>112/4 && p->map_dirty && !(uint32_t)r->map_upload && packed==384){
   /* Each 192-byte DATA is aligned to the original raw bundle's 16-byte
    * validation units. Credit, expansion checks and final coverage stay live. */
   if(!packet(s,2,5,offset,raw,192) || !packet(s,2,5,offset+192,raw+192,192))return false;
  }else if(!span(s,5,offset,raw,packed))return false;""")
            else:
                start="  if(!span(s,5,offset,raw,packed))return false;"
                end="  size[5]=(uint16_t)(offset+249);"
                text=once(text,start,"""  if(p->objects>112/4 && p->map_dirty && !(uint32_t)r->map_upload && packed==384){
   /* The expired BG key workspace already owns compact raw. Append the
    * fixed wire tables and six size bytes, excluding C alignment padding. */
   uint8_t *bundle=(uint8_t *)p->bg_keys+4096;
   memcpy(bundle+384,p->patch.mode,162);
   memcpy(bundle+546,p->patch.enable,81);
   memcpy(bundle+627,p->patch.size,6);
   for(unsigned pos=0;pos<633;pos+=240){
    unsigned n=633-pos;if(n>240)n=240;
    if(!packet(s,2,5,offset+pos,bundle+pos,n))return false;
   }
   size[5]=offset+633;
  }else{
"""+start)
                text=once(text,end,end+"\n  }")
            if mode=="rawfirst":
                marker="bool nes_sink212_seal("
                a=text.index(" if(same&&s->displayed",text.index(marker))
                b=text.index(" if(!p->scroll_issued && !span",a)
                ordinary=text[a:b]
                text=text[:a]+""" bool defer=p->objects>112/4 && p->map_dirty && !(uint32_t)r->map_upload && packed==384;
 if(!defer && !ordinary830(s,p,r,same))return false;
"""+text[b:]
                text=once(text,marker,"""static bool ordinary830(struct nes_native_sink165 *s,struct nes_native_video165 *p,struct nes_resident211 *r,bool same){
"""+ordinary+" return true;\n}\n"+marker)
                text=once(text," uint8_t descriptor[168];"," if(defer && !ordinary830(s,p,r,same))return false;\n uint8_t descriptor[168];")
            (out/name).write_text(text,newline="\n")
        return
    if mode in ("wide","widefill","wideend"):
        # Only the post-BG callback may coalesce an entire contiguous run.
        changes=[("if(!map527(s,p,map,3))","if(!map527(s,p,map,fragments>112/4 && p->map_dirty && !(uint32_t)map?5:3))"),
            ("  bool adjacent=pair","""  if(early==5){
   while(g<64 && ((mask>>g)&1))g++;
   for(unsigned at=first*64;at<g*64;){
    unsigned n=g*64-at;if(n>240)n=240;
    if(!packet(s,24,2,at,p->map+at,n))return false;
    at+=n;
   }
   s->map_next=g;continue;
  }
  bool adjacent=pair""")]
        if mode=="widefill":
            # Reuse the already verified ordinary prefix/fill writer from 827.
            base=PROBES/"nes-demo827/patch-fill/nes_native_sink165.c"
            text=base.read_text()
            for old,new in changes:
                text=once(text,old,new)
            (out/base.name).write_text(text,newline="\n")
        else:
            rewrite("nes_native_sink165.c",changes)
        if mode=="wideend":
            rewrite("nes_planner211.c",[("if(p->scroll_issued && resident->finish_obj",
                "if((p->scroll_issued || (inherit && p->map_dirty && s->counts[2]>28)) && resident->finish_obj")])
            rewrite("nes_native_runtime165.c",[("return p->sent || !p->count",
                "return (p->sent && (p->bulk_pending || !s->video->map_dirty || s->receiver->counts[2]<=28)) || !p->count")])
        return
    rows=6 if mode=="prefix" else 21
    rewrite("nes_resident211.h",[("(*offer_map)(void *,bool)","(*offer_map)(void *,unsigned)")])
    rewrite("nes_native_video165.h",[("bool scroll_issued;","bool scroll_issued;uint8_t published_right_rows;")])
    planner_changes=[("row549_done:\n","""row549_done:
 /* Only completed right-page rows can enter the transport. The lower
  * 32 row bits remain available to the ordinary end-of-frame pass. */
 if(inherit && p->published_right_rows<LIMIT && g+1>=p->published_right_rows+3u &&
    (((uint32_t)(p->map_dirty>>32)>>p->published_right_rows)&7u)==7u &&
    resident->offer_map && !resident->offer_map(resident->ctx,2))return fail(p,7);
""".replace("LIMIT",str(rows)))]
    runtime_changes=[("offer527(void *ctx,bool final)","offer527(void *ctx,unsigned final)"),
        (" return nes_sink527_early"," if(final==2)return map527(&s->sink,s->video,0,4);\n return nes_sink527_early")]
    if mode=="flight":
        planner_changes.append(("if(p->scroll_issued && resident->finish_obj",
             "if((p->scroll_issued || p->published_right_rows) && resident->finish_obj"))
        runtime_changes.append(("return p->sent || !p->count",
             "return (p->sent && (!s->video->published_right_rows || p->bulk_pending)) || !p->count"))
    if mode in ("grant","grantfill"):
        old,new=planner_changes[0]
        planner_changes[0]=(old,new.replace("if(inherit &&", "if(s->counts[2]>112/4 && inherit &&"))
    rewrite("nes_planner211.c",planner_changes)
    rewrite("nes_native_runtime165.c",runtime_changes)
    sender=""" if(early==4){
  if(s->plan->bank_history!=2 || s->plan->bulk_pending || (s->map_next&127)>32)return true;
  bool ready;
  if(!nes_plan527_map_credit(s->plan,&ready))return false;
  if(!ready)return true;
  unsigned at=2048+64*p->published_right_rows;
  if(!packet(s,24,2,at,p->map+at,192))return false;
  p->published_right_rows+=3;
  return true;
 }
 if(p->published_right_rows)mask&=~((uint64_t)((1u<<p->published_right_rows)-1u)<<32);
 bool pairable=early!=1"""
    if mode in ("grant","grantfill"):
        sender=sender.replace("nes_plan527_map_credit(s->plan,&ready)","nes_window532_room(s->plan->window,&ready)")
    rewrite("nes_native_sink165.c",[(" bool pairable=early!=1",sender)])


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("control","prefix","page","flight","wide","widefill","wideend","grant","grantfill","complete","completefill","completeraw","joined","joinedfill","rawfill","rawfirst"))
    prepare(p.parse_args().mode)
