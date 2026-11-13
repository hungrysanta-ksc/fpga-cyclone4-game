# SPDX-License-Identifier: MIT
"""Defer checked right-page cell materialization to the SPI DMA owner."""
import argparse
from pathlib import Path
from nes_raw506 import once
from prepare_nes_rows757 import prepare as rows

def prepare(base,out,serial=False,split=False,ordered=False):
    rows(base,out,'row')
    def edit(name,old,new):
        dest=out/name
        s=(dest if dest.exists() else base/name).read_text()
        dest.write_text(once(s,old,new),encoding='utf8',newline='\n')
    c='nes_planner211.c'
    edit(c,'static void map_word185', '''/* Two non-adjacent right-page triples. The ordinary map remains the source
 * for inherited cells. Queued slots are immutable until ACK or abort.
 * 384 bytes of the unused OAM workspace are available until BG completes. */
static struct {
 struct nes_native_video165 *video;
 unsigned filled,ready;
 uint8_t next[2];
} pending759;
static int range759(unsigned at){
 if(at-2048u<192)return 0;
 if(at-3008u<192)return 1;
 return -1;
}
static unsigned offset759(unsigned i){return i?3008:2048;}
static void store759(struct nes_native_video165 *p,unsigned at,unsigned word){
 if(p->map[at]!=(uint8_t)word || p->map[at+1]!=(word>>8))
  p->map_dirty|=UINT64_C(1)<<(at/64);
 p->map[at]=(uint8_t)word;p->map[at+1]=(uint8_t)(word>>8);
}
/* At most one cell per call between CF86 checks. Never calls SPI, allocates
 * slots or publishes credit. FFFF is outside the legal BG word encoding. */
bool __attribute__((noinline)) nes_map759_step(void){
 unsigned mask=pending759.ready;
 if(!mask)return false;
 unsigned i=(mask&1)?0:1,j=pending759.next[i]++;
 struct nes_native_video165 *p=pending759.video;
 unsigned word;uint16_t value;
 memcpy(&value,p->oam+i*192+j*2,2);word=value;
 if(word!=65535)store759(p,offset759(i)+j*2,word);
 if(j==95)pending759.ready&=~(1u<<i);
 return true;
}
static unsigned read759(struct nes_native_video165 *p,unsigned at){
 int i=range759(at);
 if(pending759.video && i>=0 && (pending759.filled&(1u<<i))){
  uint16_t value;memcpy(&value,p->oam+i*192+at-offset759(i),2);
  if(value!=65535)return value;
 }
 return (unsigned)p->map[at]|((unsigned)p->map[at+1]<<8);
}
static void map_word185''')
    start=' if(p->map[at]!=(uint8_t)word||p->map[at+1]!=(uint8_t)(word>>8))p->map_dirty|=UINT64_C(1)<<(at/64);\n p->map[at]=(uint8_t)word;p->map[at+1]=(uint8_t)(word>>8);'
    edit(c,start,''' int i=range759(at);
 if(!pending759.video || i<0){store759(p,at,word);return;}
 unsigned mask=1u<<i;
 if(!(pending759.filled&mask)){
  memset(p->oam+i*192,255,192);pending759.filled|=mask;
 }
 uint16_t value=(uint16_t)word;
 memcpy(p->oam+i*192+at-offset759(i),&value,2);''')
    edit(c,'unsigned word=(unsigned)p->map[old_at]|((unsigned)p->map[old_at+1]<<8);','unsigned word=read759(p,old_at);')
    edit(c,' unsigned next_offer=3;', ''' pending759.video=inherit?p:NULL;pending759.filled=pending759.ready=0;
 pending759.next[0]=pending759.next[1]=0;
 unsigned next_offer=3;''')
    edit(c,'row549_done:\n','''row549_done:
  if(g==2 || g==17)pending759.ready|=pending759.filled&(1u<<(g==17));
''')
    # Start offering after three more groups so a prior E1 can write the next
    # immutable range while the consumer is still retiring earlier packets.
    edit(c,'if((g+1)%3==0 && resident->offer_map &&','if(g>=8 && (g+1)%3==0 && resident->offer_map &&')
    edit(c,'resident->ctx,2+(g+1)/3','resident->ctx,2+(g+1)/3-1')
    edit(c,' } /* compact groups */',''' } /* compact groups */
 /* A sparse/short frame may end halfway through either target. */
 pending759.ready=pending759.filled;
 for(unsigned i=0;i<2;i++)if(pending759.next[i]==96)pending759.ready&=~(1u<<i);
 while(nes_map759_step()){}
 pending759.video=NULL;''')
    # Finish only ranges needed for this packet before inspecting dirty bits.
    edit(c,'static unsigned read759','''void nes_map759_finish(unsigned at,unsigned n){
 for(unsigned i=0;i<2;i++){
  unsigned start=offset759(i);
  if(at<start+192 && at+n>start){
   while(pending759.ready&(1u<<i))nes_map759_step();
  }
 }
}
static unsigned read759''')
    h='nes_resident211.h'
    edit(h,'void nes_resident211_reset','void nes_map759_finish(unsigned,unsigned);\nbool nes_map759_step(void);\nvoid nes_resident211_reset')
    # Clear the pointer on every planner exit, even on STOP/error, before
    # returning to any owner that can reuse or release the frame workspace.
    edit(c,'  p->valid=false;nes_resident211_abort(resident);return false;', '  pending759.ready=0;pending759.video=NULL;\n  p->valid=false;nes_resident211_abort(resident);return false;')
    edit('nes_native_sink165.c','  if((s->right757&(1u<<i))', '''  nes_map759_finish(row*64,192);
  pending|=p->map_dirty;
  if((s->right757&(1u<<i))''')
    # A planner's left page callback must not cross into uncompleted right
    # rows. All right page publications during BG use the bounded frontier.
    edit('nes_native_runtime165.c',' return map527(&s->sink,s->video,\n   s->resident->map_stale[s->resident->target]|s->video->map_dirty,mode);',''' uint64_t mask=s->resident->map_stale[s->resident->target]|s->video->map_dirty;
 if(!final)mask&=UINT32_MAX;
 return map527(&s->sink,s->video,mask,mode);''')
    edit('nes_dma182.inc','static bool nes182_run(void){','extern bool nes_map759_step(void);\nstatic bool __attribute__((noinline,noclone)) nes182_run(bool map){')
    edit('nes_dma182.inc','  if(left==last)', '''  if(map && !nes_map759_step())map=false;
  if(left==last)''')
    edit('nes_native165_bulk.inc','if(!nes182_run())','if(!nes182_run(count>=19 && tx[0]==0xe1 && tx[1]==2 && tx[2]==2))')

    if split or ordered:
        # Give completed ranges a bounded part of the DMA window. Materialize
        # the remainder after the packet is visible to the independent CPU.
        edit('nes_dma182.inc','unsigned last=0xffffffffu,idle=0;', 'unsigned last=0xffffffffu,idle=0,quota=32;')
        edit('nes_dma182.inc','if(map && !nes_map759_step())map=false;',
             'if(map && (!quota-- || !nes_map759_step()))map=false;')
        edit('nes_native_sink165.c','  s->sequence++;s->state=old;return true;',
             '  if(b[0]==2 && section==2)while(nes_map759_step()){}\n  s->sequence++;s->state=old;return true;')
    if ordered:
        # Same global FIFO order as 753. Changing only idle-DMA selection
        # cannot merge two map descriptors separated by a left-page/tile head.
        for name in ('nes_native_runtime165.c','nes_native_sink165.c','nes_native_sink165.h','nes_resident211.h'):
            (out/name).write_bytes((base/name).read_bytes())
        h='nes_resident211.h'
        edit(h,'void nes_resident211_reset','bool nes_map759_step(void);\nvoid nes_resident211_reset')
        dest=out/c
        s=dest.read_text()
        a=s.index('  /* Both physical pages');b=s.index(' } /* compact groups */',a)
        dest.write_text(s[:a]+s[b:],newline='\n')
        # Left-page offers use the original cursor; a sparse left page could
        # skip to an unfinished right page. Restrict only the non-final scan.
        edit('nes_native_runtime165.c','s->resident->map_stale[s->resident->target]|s->video->map_dirty,mode);',
             '(s->resident->map_stale[s->resident->target]|s->video->map_dirty) & (final?UINT64_MAX:UINT32_MAX),mode);')
        edit('nes_native_sink165.c','  s->sequence++;s->state=old;return true;',
             '  if(b[0]==2 && section==2)while(nes_map759_step()){}\n  s->sequence++;s->state=old;return true;')
    if serial:
        # Preserve the producer/frontier and exercise the same TC loop, but
        # materialize a pending range only in the foreground.
        edit('nes_dma182.inc','if(map && !nes_map759_step())map=false;', '(void)map;')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','out'):p.add_argument(k,type=Path)
    mode=p.add_mutually_exclusive_group()
    mode.add_argument('--serial',action='store_true');mode.add_argument('--split',action='store_true')
    mode.add_argument('--ordered',action='store_true')
    a=p.parse_args();prepare(a.base,a.out,a.serial,a.split,a.ordered)
