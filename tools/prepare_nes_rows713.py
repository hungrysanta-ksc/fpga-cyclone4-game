"""Replace ascending map ownership with two bounded row cursors.

The planner publishes completed logical rows, never an in-progress row.
Use existing E8/E9, checked queue credit and bulk ownership without new ABI.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

def run(a):
    assert sha(a.base/'obj-nes-100/firmware.stm') in ('b5c42303c6831190f77c95367bd1640e3e575caea8e3909af27e2587ad5eb600','a1408f18a82602aa54fb67607c933c7dd5de79213e43adc1d2ee185ca3ae712a')
    names=('nes_native_sink165.c','nes_native_sink165.h','nes_native_runtime165.c','nes_planner211.c','nes_resident211.h')
    f={n:(a.base/n).read_text() for n in names}
    n='nes_native_sink165.h'
    f[n]=once(f[n],'bool map_pair683; /* Existing alignment padding. */','bool map_pair683; uint8_t map_other,map_ready,map_page;')
    f[n]=once(f[n],'bool nes_sink527_early(struct nes_native_sink165 *,struct nes_native_video165 *,struct nes_resident211 *,bool);\n','')
    f[n]=f[n].replace('/* 0: output, 1: row offer, 2: BG complete */','/* 0: output, 1: checked producer yield, 3: row offer */')
    n='nes_resident211.h';f[n]=once(f[n],'bool (*offer_map)(void *,bool); /* true: all BG rows are final */','bool (*offer_map)(void *,unsigned); /* completed logical rows, 32 after BG */')
    n='nes_native_sink165.c';s=f[n]
    s=once(s,'s->map_next=0;s->map_pair683=false;','s->map_next=s->map_other=s->map_ready=s->map_page=0;s->map_pair683=false;')
    start=s.index('bool map527(');end=s.index('static bool __attribute__((noinline)) same635',start)
    s=s[:start]+'''bool map527(struct nes_native_sink165 *s,struct nes_native_video165 *p,uint64_t mask,unsigned early){
 bool pairable=early!=3 && s->plan && s->plan->bank_history==2 && s->plan->window;
 bool pair=pairable && s->map_pair683 && s->plan->window->last[0]==2 && s->plan->window->last[1]==2;
 s->map_pair683=false;
 unsigned page=early?s->map_page:0,empty=0;
 for(;;){
  uint8_t *cursor=page?&s->map_other:&s->map_next;
  unsigned g=*cursor,limit=early?s->map_ready:32;
  uint32_t bits=page?(uint32_t)(mask>>32):(uint32_t)mask;
  while(g<limit && !((bits>>g)&1)){g++;pair=false;}
  *cursor=g;
  if(g==limit){if(++empty==2)return true;page^=1;continue;}
  empty=0;
  unsigned first=g++,count=1;while(g<limit&&count<3&&((bits>>g)&1)){g++;count++;}
  if(early==3){bool ready;if(!nes_plan527_map_credit(s->plan,&ready))return false;if(!ready)return true;}
  if(!packet(s,(early || (pair&&count==3))?24:2,2,(page*32+first)*64,p->map+(page*32+first)*64,count*64))return false;
  *cursor=g;s->map_page=page^1;
  pair=pairable && count==3 && s->map_pair683;s->map_pair683=false;
  if(early)return true;
 }
}
'''+s[end:];f[n]=s
    n='nes_planner211.c';s=f[n];s=once(s,' unsigned next_offer=3;\n','')
    start=s.index('  /* Physical rows g and g+32');end=s.index('  nes_cost474_groups++;',start)
    s=s[:start]+s[end:]
    anchor='row549_done:\n'
    s=once(s,anchor,anchor+' if(resident->offer_map && (g+1)%3==0 && !resident->offer_map(resident->ctx,g+1))return fail(p,7);\n')
    s=once(s,'resident->offer_map(resident->ctx,next_offer!=3)','resident->offer_map(resident->ctx,32)');f[n]=s
    n='nes_native_runtime165.c';s=f[n];start=s.index('static bool offer527(');end=s.index('static bool planner221',start)
    s=s[:start]+'''static bool quiet528(void *ctx){
 struct nes_native_runtime165 *s=ctx;
 unsigned before=s->sink.sequence;
 if(!map527(&s->sink,s->video,s->resident->map_stale[s->resident->target]|s->video->map_dirty,1))return false;
 if(s->sink.sequence==before)s->plan.quiet_map=NULL;
 return true;
}
static bool offer527(void *ctx,unsigned rows){
 struct nes_native_runtime165 *s=ctx;
 s->sink.map_ready=rows;s->plan.quiet_map=quiet528;
 return map527(&s->sink,s->video,s->resident->map_stale[s->resident->target]|s->video->map_dirty,3);
}
'''+s[end:];f[n]=s
    if a.first_bg:
        f[n]=once(f[n],' s->sink.map_ready=rows;s->plan.quiet_map=quiet528;',
            ' s->sink.map_ready=rows;\n /* Do not let a completed map row postpone the first new BG plan. */\n if(rows<32 && !s->plan.early)return true;\n s->plan.quiet_map=quiet528;')
    a.out.mkdir(parents=True,exist_ok=False)
    for n,s in f.items():(a.out/n).write_text(s,encoding='utf8',newline='\n')
    (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage=713,first_BG_priority=a.first_bg,scope=__doc__,base={n:sha(a.base/n) for n in names},patch={n:sha(a.out/n) for n in names}),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--first-bg',action='store_true')
    run(p.parse_args())
