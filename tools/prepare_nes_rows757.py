# SPDX-License-Identifier: MIT
"""Offer immutable three-row right-page ranges to the existing checked map queue."""
import argparse
from pathlib import Path
from nes_raw506 import once,sha


def prepare(base,out,mode):
    assert sha(base/'obj-nes-100/firmware.stm')=='192cf5becb19bb58ede0be25be73d91e4c1fee1f836eadabcb9999ac2af929a6'
    out.mkdir(parents=True,exist_ok=False)
    def edit(name,changes):
        content=(base/name).read_text()
        for old,new in changes:content=once(content,old,new)
        (out/name).write_text(content,encoding='utf8',newline='\n')
    batch={'row':1,'pair':2,'page':8}[mode]
    end_batch=f'if({batch}==1 || (i&1))break;' if batch<8 else 'if(i==7)break;'
    edit('nes_resident211.h',[('(*offer_map)(void *,bool)','(*offer_map)(void *,unsigned)')])
    edit('nes_planner211.c',[(' } /* compact groups */',f'''  /* Both physical pages of rows 0..g have final words and slot owners. */
  if((g+1)%{3*batch}==0 && resident->offer_map &&
     !resident->offer_map(resident->ctx,2+(g+1)/3))return fail(p,7);
 }} /* compact groups */''')])
    edit('nes_native_sink165.h',[('uint8_t map_next;', 'uint8_t map_next,right757;')])
    edit('nes_native_sink165.c',[('s->map_next=0;s->map_pair683','s->map_next=0;s->right757=0;s->map_pair683'),
        (' bool pairable=early', ''' /* Exclude only accepted, complete triplets. Keep the left-page cursor intact. */
 for(unsigned i=0,b=s->right757;b;i++,b>>=1)
  if(b&1)mask&=~(UINT64_C(7)<<(32+i*3));
 bool pairable=early'''),
        ('static bool __attribute__((noinline)) same635', '''bool nes_map757_offer(struct nes_native_sink165 *s,struct nes_native_video165 *p,
                      uint64_t pending,unsigned finished){
 for(unsigned i=0;i<finished && i<8;i++){
  unsigned row=32+3*i;
  if((s->right757&(1u<<i)) || (s->map_next&127)>row || ((pending>>row)&7)!=7)continue;
  bool ready;
  if(!nes_window532_room(s->plan->window,&ready))return false;
  if(!ready)return true;
  if(!nes_plan527_map_credit(s->plan,&ready))return false;
  if(!ready)return true;
  if(!packet(s,24,2,row*64,p->map+row*64,192))return false;
  s->right757|=1u<<i;
  END_BATCH
 }
 return true;
}
static bool __attribute__((noinline)) same635'''.replace('END_BATCH',end_batch))])
    edit('nes_native_runtime165.c',[('static bool offer527(void *ctx,bool final)', '''extern bool nes_map757_offer(struct nes_native_sink165 *,struct nes_native_video165 *,uint64_t,unsigned);
static bool offer527(void *ctx,unsigned final)'''),
        (' unsigned mode=final?2:1;', ''' if(final>1){
  if(s->plan.bank_history!=2 || !s->plan.early)return true;
  return nes_map757_offer(&s->sink,s->video,
      s->resident->map_stale[s->resident->target]|s->video->map_dirty,final-2);
 }
 unsigned mode=final?2:1;''')])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','out'):p.add_argument(name,type=Path)
    p.add_argument('mode',choices=('row','pair','page'))
    a=p.parse_args()
    prepare(a.base,a.out,a.mode)
