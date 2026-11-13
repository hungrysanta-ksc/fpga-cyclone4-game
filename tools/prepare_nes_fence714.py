"""Pay a final BG plan flush before OBJ; lend real waits to contiguous map.

No row-triggered SPI, speculative ROM read, new wire ABI or delay constant.
This is a bounded schedule experiment, not a selected production change.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

def run(a):
    assert sha(a.base/'obj-nes-100/firmware.stm') in (
        'b5c42303c6831190f77c95367bd1640e3e575caea8e3909af27e2587ad5eb600',
        'a1408f18a82602aa54fb67607c933c7dd5de79213e43adc1d2ee185ca3ae712a')
    names=('nes_planner211.c','nes_native_runtime165.c','nes_native_sink165.c','nes_native_sink165.h')
    f={n:(a.base/n).read_text() for n in names}
    n='nes_planner211.c';s=once(f[n],' unsigned next_offer=3;\n','')
    lo=s.index('  /* Physical rows g and g+32');hi=s.index('  nes_cost474_groups++;',lo)
    s=s[:lo]+s[hi:]
    s=once(s,'resident->offer_map(resident->ctx,next_offer!=3)','resident->offer_map(resident->ctx,true)')
    s=once(s,' /* No OBJ/raw operation below writes map. A completed offer may only\n  * continue the exact683 map prefix; cold and other heads keep old priority. */',
        ' /* Both pages are immutable now. Flush remaining BG records before\n  * OBJ preparation; only actual producer waits may borrow map packets. */')
    f[n]=s
    n='nes_native_runtime165.c';s=f[n]
    lo=s.index('static bool offer527(');hi=s.index('static bool quiet528(',lo)
    s=s[:lo]+s[hi:]
    s=once(s,'map527(&s->sink,s->video,s->resident->map_upload,true)',
        'map527(&s->sink,s->video,s->resident->map_stale[s->resident->target]|s->video->map_dirty,true)')
    at=s.index('static bool planner221(')
    s=s[:at]+'''static bool offer527(void *ctx,bool final){
 struct nes_native_runtime165 *s=ctx;
 (void)final;
 /* The only caller is after all BG groups; this is not a row-ready guess.
  * drive554 retains E9/ready-tile priority and checked queue/bulk ownership. */
 s->plan.quiet_map=quiet528;
 return nes_plan549_first(&s->plan);
}
'''+s[at:]
    f[n]=s
    n='nes_native_sink165.c';s=f[n];lo=s.index('bool nes_sink527_early(');hi=s.index('static bool __attribute__((noinline)) same635',lo)
    f[n]=s[:lo]+s[hi:]
    n='nes_native_sink165.h';f[n]=once(f[n],'bool nes_sink527_early(struct nes_native_sink165 *,struct nes_native_video165 *,struct nes_resident211 *,bool);\n','')
    a.out.mkdir(parents=True,exist_ok=False)
    for n,s in f.items():(a.out/n).write_text(s,encoding='utf8',newline='\n')
    (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage=714,scope=__doc__,base={n:sha(a.base/n) for n in names},patch={n:sha(a.out/n) for n in names}),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
