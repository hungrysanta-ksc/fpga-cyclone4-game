# SPDX-License-Identifier: MIT
"""Supply frozen map rows during OBJ ROM stalls using the existing bounded credit path."""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

def prepare(src,out,offer=False,after_tile=False):
    root=Path(__file__).resolve().parents[1]
    assert sha(src/'obj-nes-100/firmware.stm')==json.loads((root/'analysis/windows541-verification.json').read_text())['firmware_SHA256']
    out.mkdir(parents=True,exist_ok=False)
    def write(name,s): (out/name).write_text(s,encoding='utf8',newline='\n')
    name='nes_resident211.h'
    write(name,once((src/name).read_text(),'bool (*offer_map)(void *);','bool (*offer_map)(void *,bool);'))
    name='nes_planner211.c';s=(src/name).read_text()
    assert s.count('resident->offer_map(resident->ctx)')==2
    s=s.replace('resident->offer_map(resident->ctx)','resident->offer_map(resident->ctx,false)')
    s=once(s,' /* No callback retains scratch pointers;', ''' /* All map writes are complete. OBJ/raw preparation below does not change
  * the map. Arm the existing credit-bounded callback, without issuing SPI or
  * delaying the first BG plan. No beam estimate or new wire hint is used. */
 if(resident->offer_map && !resident->offer_map(resident->ctx,true))return fail(p,7);

 /* No callback retains scratch pointers;''')
    write(name,s)
    name='nes_native_runtime165.c';s=(src/name).read_text()
    s=once(s,'static bool offer527(void *ctx){','static bool quiet528(void *ctx);\nstatic bool offer527(void *ctx,bool frozen){')
    s=once(s,' return nes_sink527_early(&s->sink,s->video,s->resident);', ''' if(frozen){s->plan.quiet_map=quiet528;return true;}
 return nes_sink527_early(&s->sink,s->video,s->resident);''')
    if offer:
        s=once(s,'if(frozen){s->plan.quiet_map=quiet528;return true;}', '''if(frozen){
  if(s->transport.error || s->plan.error || s->sink.state!=NES_SINK165_BUILD)return false;
  s->plan.quiet_map=quiet528;
  /* One immutable packet, only with spare credit and no ready tile. Never
   * wait for a queue drain or expire an unresolved bulk retirement target. */
  bool room;
  if(!nes_window532_room(&s->transport,&room))return false;
  if(!room || (s->plan.bulk_pending && (uint16_t)(s->transport.sent-s->plan.bulk_until)>=3))return true;
  if(!nes_plan527_map_credit(&s->plan,&room))return false;
  return !room || quiet528(ctx);
 }''')
        if after_tile:
            s=once(s,'''  if(!nes_plan527_map_credit(&s->plan,&room))return false;
  return !room || quiet528(ctx);''','''  uint16_t before=s->transport.sent;
  if(!nes_plan527_map_credit(&s->plan,&room))return false;
  /* A freshly submitted tile already owns the earlier queue position. Only
   * then offer one map behind it; a repeated descriptor grants nothing. */
  if(!room && s->transport.sent==before)return true;
  if((uint16_t)(s->transport.sent-s->transport.retired)>=3)return true;
  return quiet528(ctx);''')
    s=once(s,' unsigned before=s->sink.map_next;', ''' if(!s->resident->open || s->resident->fault ||
    s->resident->generation!=s->sink.generation || s->video->generation!=s->sink.generation)return false;
 unsigned before=s->sink.map_next;''')
    s=once(s,'s->resident->map_upload,true','s->resident->map_stale[s->resident->target]|s->video->map_dirty,true')
    s=once(s,'  s->plan.quiet_map=quiet528;\n  bool end_ok=', '  bool end_ok=')
    s=once(s,' if(s->resident)nes_resident211_abort(s->resident);',' s->plan.quiet_map=NULL;\n if(s->resident)nes_resident211_abort(s->resident);')
    write(name,s)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--offer',action='store_true')
    p.add_argument('--after-tile',action='store_true')
    a=p.parse_args()
    if a.after_tile and not a.offer:p.error('--after-tile requires --offer')
    prepare(a.arm,a.out,a.offer,a.after_tile)
