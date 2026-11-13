"""717 plus checked map retirement / useful bounded input before ordinary.

Replace historical palette silence and OAM repeated drain with real progress.
No new wire ABI, static storage, FPGA or SNES code.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

def run(a):
 assert sha(a.base/'obj-nes-100/firmware.stm') in (
  'ed03f17450b41b1617e9306c43100d0c9e9a1ea6256d815c24bf2547ab8381c8',
  'a08cbf4585e14aedea2570e979de3b3468ceec08e186cb317b9ba1a8c76a190f')
 names=('nes_native_runtime165.c','nes_native_sink165.c')
 f={n:(a.base/n).read_text() for n in names}
 n=names[0];s=f[n]
 s=once(s,'   if(reason!=2)break;','''   if(reason!=2){
    if(reason!=4)break;
    /*718 Recheck checked retirement/progress after each useful input block.
     * An empty input or exhausted seven-block allowance returns immediately.
     * Receipt/progress never permits input COMMIT or acknowledges display. */
    uint8_t ack[12];
    if(!nes_window184_drain(&s->transport,ack))return fail(s,NES_RUNTIME165_DISPLAY);
    if(s->transport.status_flags&8)break;
   }''');f[n]=s
 n=names[1];s=f[n]
 begin=s.index(' /* The original span still owns packet boundaries')
 end=s.index(' if(op==24)',begin)
 s=s[:begin]+s[end:]
 begin=s.index(' /* Allow a long accepted map tail')
 end=s.index('  /* Canonical raw CHR',begin)
 s=s[:begin]+''' /*718 Before immutable ordinary heads, retire a real warm map tail.
  * Lend only useful next-input work until actual DMA progress; STOP and new
  * packets keep SNES priority. No fixed silence or presumed VRAM completion. */
 if(s->plan && s->plan->bank_history==2 && s->plan->window &&
    s->plan->window->last[1]==2){
  struct nes_sink_window184 *w=s->plan->window;uint8_t ack[12];
  if(!nes_window184_drain(w,ack) ||
     (!(w->status_flags&8) && w->wait &&
      !w->wait(w->ctx,w->guard,4,false)))return fail(s,5);
 }
'''+s[end:]
 s=once(s,''' if((((uint32_t)(r->map_upload>>32))&0x7ffffu)==0x7ffffu && s->plan){
  for(unsigned i=0;i<2;i++)
   if(!nes_cost474_pause(s->plan->ctx,s->plan->guard,0,false))return fail(s,5);
 }
''','');f[n]=s
 a.out.mkdir(parents=True,exist_ok=False)
 for n,s in f.items():(a.out/n).write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage=718,
  base_firmware=sha(a.base/'obj-nes-100/firmware.stm'),changed={n:sha(a.out/n) for n in names},
  new_static_RAM_B=0,new_RTL=False,new_65816=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
