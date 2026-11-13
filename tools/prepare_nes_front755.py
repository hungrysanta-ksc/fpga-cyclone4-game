# SPDX-License-Identifier: MIT
"""Build 753 overlays for input during the old receipt and cold-safe BG index preparation."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha


def prepare(base, out, policy):
    assert sha(base/'src/obj-nes-100/firmware.stm')=='192cf5becb19bb58ede0be25be73d91e4c1fee1f836eadabcb9999ac2af929a6'
    out.mkdir(parents=True,exist_ok=False)
    def source(name):
        return (base/'src'/name).read_text()
    def save(name,s):
        (out/name).write_text(s,encoding='utf8',newline='\n')
    # Named overlays isolate timing and fit regressions from the common 753 link.
    base_policy=policy
    if policy in ('frozen','paired','geometry'):
        policy='receive'
    if policy in ('empty','fast','service'):
        policy='stream'
    if policy in ('receive','index','joint','stream'):
        name='nes_native_runtime165.c'
        s=source(name)
        # Keep the previous output ownership until terminal ACK+EA. Service
        # at most one bounded next input group per callback during ordinary.
        start=s.index('   if(!s->prefetch_left && s->plan.bank_history')
        end=s.index('\n   }',start)+5
        s=s[:start]+s[end:]
        s=once(s,'s->prefetch_left=7;', 's->prefetch_left=s->plan.bank_history==2?24:7;')
        if policy=='stream':
            s=once(s,'if(reason!=2)break;', 'if(reason!=2 || (progress && !r->ready183))break;')
        if policy in ('index','joint','stream'):
            s=once(s,'  if(reason==3)reason=2;', '''  if(reason==3){
   if(s->resident && s->resident->prepared)nes_resident755_index(s->resident);
   reason=2;
  }''')
            h='nes_resident211.h'
            save(h,once(source(h),'void nes_resident211_reset','void nes_resident755_index(struct nes_resident211 *);\nvoid nes_resident211_reset'))
            c='nes_resident211.c'
            # Only the real SEAL invokes the early rebuild. Preserve the
            # standalone begin API when the caller cannot supply that hook.
            htext=(out/h).read_text()
            save(h,once(htext,' uint16_t bg[1024];',' bool index_ready755;\n uint16_t bg[1024];'))
            r=once(source(c),'static unsigned find221(','''void nes_resident755_index(struct nes_resident211 *s){
 rebuild221(s);s->index_ready755=true;
}
static unsigned find221(''')
            r=once(r,'if(s->epoch!=epoch){','if(s->epoch!=epoch){\n  s->index_ready755=false;')
            r=once(r,' rebuild221(s);\n return true;', ' if(!s->index_ready755)rebuild221(s);\n s->index_ready755=false;\n return true;')
            save(c,r)
        save(name,s)
    if base_policy=='geometry':
        # Seven 256-byte patches occupy at most 1792 bytes. After META_END,
        # the last 256 bytes of the former requirement bitmap are free.
        c='nes_native165.c'
        h='nes_native165.h'
        save(h,once(source(h),'bool ready183;','bool ready183;bool bg_fine_ready755;'))
        s=once(source(c),'  s->missing=0;s->next_kind=7;','''  uint8_t *fine_y=s->raw_pixels+7*256;
  for(unsigned y=0;y<224;y++)fine_y[y]=s->rows[y]&7;
  for(unsigned i=0;i<s->counts[3];i++){
   unsigned v=s->exceptions[i],pos=(v>>6)&8191;
   if(!(pos%33))fine_y[pos/33]=(v>>3)&7;
  }
  s->bg_fine_ready755=true;
  s->missing=0;s->next_kind=7;''')
        save(c,s)
        c='nes_planner211.c'
        s=source(c)
        mark='static unsigned fine(const struct nes_native165 *s,unsigned y,unsigned x,bool low){'
        s=once(s,mark,mark+'\n if(!x && !low && s->bg_fine_ready755)return s->raw_pixels[7*256+y];')
        save(c,s)
    if base_policy in ('frozen','paired'):
        # The final callback is past the last BG row. Subsequent OBJ and raw
        # planning cannot modify its map. Advance the same checked cursor.
        name='nes_native_runtime165.c'
        s=(out/name).read_text()
        marker=' if(s->sink.map_next>=64)return true;'
        s=once(s,marker,marker+'''
 if(final && s->plan.bank_history==2 && s->plan.early){
  uint64_t mask=s->resident->map_stale[s->resident->target]|s->video->map_dirty;
  while(s->sink.map_next<64){
   unsigned before=s->sink.map_next;
   bool room;
   if(!nes_plan527_map_credit(&s->plan,&room))return false;
   if(!room)break;
   if(!map527(&s->sink,s->video,mask,3))return false;
   if(s->sink.map_next==before)break;
  }
  return true;
 }''')
        if base_policy=='frozen':
            start=s.index('  while(s->sink.map_next<64)')
            end=s.index('  return true;',start)
            s=s[:start]+'''  if(!map527(&s->sink,s->video,mask,0))return false;
  s->sink.map_next=64;
'''+s[end:]
        save(name,s)
    if policy in ('wire','joint','stream'):
        c='nes_sink_window184.c'
        s=once(source(c),'if(s->ever_sent && (p[0]!=3', 'if(s->ever_sent && !(p[0]==1 && s->last[0]==3 && s->sent==s->retired) && (p[0]!=3')
        save(c,s)
        c='nes_native165.c'
        s=source(c)
        # Keep the final POP confirmation only if it certifies COMPLETE. Its
        # token, CRC and prepare bit are checked again at prepare entry.
        s=once(s,'if(s->state==NES_NATIVE165_RECEIVING && (rx[2]&1)){','if((s->state==NES_NATIVE165_RECEIVING && (rx[2]&1)) ||\n    (s->state==NES_NATIVE165_COMPLETE && (rx[2]&2))){')
        s=once(s,' s->ready183=false;\n uint8_t tx[8],rx[8];frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8)||!status(rx)||!(rx[2]&2))return fail(s,25);',''' uint8_t tx[8],rx[8];
 if(s->ready183){memcpy(rx,s->status183,8);s->ready183=false;}
 else{frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8))return fail(s,25);}
 if(!status(rx)||!(rx[2]&2)||((rx[3]<<8)|rx[4])!=s->next_token)return fail(s,25);''')
        # Reuse the same CRC-8/ATM implementation already linked for E8.
        a=s.index('static uint8_t crc8(');b=s.index('static bool fail(',a)
        s=s[:a]+'extern uint8_t nes_wire723_crc8(const uint8_t *,unsigned);\n#define crc8 nes_wire723_crc8\n'+s[b:]
        save(c,s)
    if policy=='stream' and base_policy not in ('fast','service'):
        c='nes_native_sink165.c'
        s=once(source(c),' if(op==24)op=2;', ''' if(section==5 && s->plan && s->plan->finished && s->plan->bank_history==2){
  struct nes_sink_window184 *w=s->plan->window;
  if(w && w->wait && !w->wait(w->ctx,w->guard,4,false))return fail(s,5);
 }
 if(op==24)op=2;''')
        if base_policy=='empty':
            s=s.replace('w && w->wait && !w->wait','w && w->sent==w->retired && w->wait && !w->wait')
        save(c,s)


    if base_policy in ('empty','fast','service'):
        # Every bit of a valid raw color is checked before the conversion.
        # Each half-word product collects four pixel bits in screen order.
        c='nes_planner211.c'
        s=source(c)
        a=s.index('   for(unsigned x=0;x<256;x++)for(unsigned plane=0;plane<8;plane++)')
        b=s.index('\n  }',a)
        s=s[:a]+"""   for(unsigned tile=0;tile<32;tile++){
    uint32_t hi,lo;memcpy(&hi,pixels+8*tile,4);memcpy(&lo,pixels+8*tile+4,4);
    uint8_t *dst=p->patch.chr+64*tile+2*slot;
    for(unsigned pair=0;pair<3;pair++,dst+=16)for(unsigned j=0;j<2;j++){
     unsigned a=((hi&0x01010101u)*0x08040201u)>>24;
     unsigned b=((lo&0x01010101u)*0x08040201u)>>24;
     dst[j]=(uint8_t)((a<<4)|b);hi>>=1;lo>>=1;
    }
    dst[0]=255;
   }"""+s[b:]
        # Used-key lookups require the owning used bit. Each used slot is
        # initialized on insertion. Keep map inheritance and zero every
        # published OAM, CGRAM, HDMA and raw byte through their normal paths.
        s=once(s,' memset(p,0,offsetof(struct nes_native_video165,map));','')
        save(c,s)
    if base_policy=='service':
        # Ordinary enqueue already performed head arbitration and copied its
        # bytes. This opportunity is independent of the empty-queue reason 4.
        # Do not touch the receiver until the previous planner is finished.
        c='nes_sink_window184.c'
        s=(out/c).read_text()
        s=once(s,' return send(s,p,n);',' if(!send(s,p,n))return false;\n return p[1]!=5 || !s->wait || s->wait(s->ctx,s->guard,5,false);')
        save(c,s)
        c='nes_native_runtime165.c'
        s=(out/c).read_text()
        anchor=' bool input_wait=reason<=1 && s->plan.finished && !progress;'
        s=once(s,anchor,' if(reason==5){\n  if(!s->plan.ending || !s->plan.bank_history || r->state==NES_NATIVE165_COMPLETE)return true;\n  if(!check(ctx))return false;\n  nes_native165_consumed(r);\n  return nes_native165_poll(r,transfer,s)||fail(s,NES_RUNTIME165_RECEIVE);\n }\n'+anchor)
        # Earlier ordinary prefetch can leave a receiving rather than COMMITTED
        # context. SEAL entry still owns exactly one capped input batch.
        s=once(s,'if(r->state==NES_NATIVE165_COMMITTED)s->prefetch_left=', 'if(reason==3 || r->state==NES_NATIVE165_COMMITTED)s->prefetch_left=')
        save(c,s)
        for c in ('nes_native165.c','nes_native_runtime165.c','nes_resident211.c','nes_planner211.c',
                  'nes_plan_service200.c','nes_sink_window184.c','nes_native_sink165.c','nes_budget210.c'):
            path=out/c
            old=path.read_text() if path.exists() else source(c)
            save(c,'#pragma GCC optimize ("Oz")\n'+old)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('base','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--policy',choices=('receive','index','wire','joint','stream','empty','fast','service','frozen','paired','geometry'),required=True)
    a=p.parse_args()
    prepare(a.base,a.out,a.policy)
