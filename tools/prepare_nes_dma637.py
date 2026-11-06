# SPDX-License-Identifier: MIT
"""Give the already accepted dense OBJ/map list an empty queue before the raw tail."""
import argparse
import json
import shutil
from pathlib import Path
from nes_raw506 import once, sha


def prepare(base, out, after_map=False, receive=False, late_receive=False, late_blocks=3):
    reference = json.loads(Path('analysis/export636-verification.json').read_bytes())
    assert sha(base/'src/obj-nes-100/firmware.stm') == reference['checks']['arm02']['firmware']
    shutil.copytree(base, out, ignore=shutil.ignore_patterns('obj-*', '.dep-*', '*.log'))
    sink = out/'src/nes_native_sink165.c'
    anchor = ' if(!span(s,5,0,p->hdma,p->hdma_size))return false;'
    if receive or late_receive:
        # The sink now owns final video and resident data. Only D0/D1/D2
        # may run here. The existing outer runtime still owns D3 after EA.
        runtime=out/'src/nes_native_runtime165.c'
        code=once(runtime.read_text(),'if(ok&&seal)s->prefetch_left=7;',
                  'if(ok&&seal&&s->receiver->state==NES_NATIVE165_COMMITTED)s->prefetch_left=7;')
        code=once(code,' if(s->prefetch_left&&reason==2&&!progress){',""" if(reason==3){
  if(s->receiver->state==NES_NATIVE165_COMMITTED)s->prefetch_left=7;
  reason=2;
 }
 if(s->prefetch_left&&reason==2&&!progress){""")
        runtime.write_text(code,newline='\n')
        drain='  if(!nes_window184_drain(s->plan->window,ack))return fail(s,5);'
        window="""
  if(s->displayed && s->obj_next>=16 && s->plan->window->wait){
   for(unsigned slot=0;slot<3;slot++)
    if(!s->plan->window->wait(s->plan->ctx,s->plan->guard,3,false))return fail(s,5);
  }"""
        if late_receive:
            # Cover the capture-in-progress interval with checked service. In
            # the final three slots the same callback may restore real input.
            window=once(window,'slot<3','slot<40')
            window=once(window,'guard,3,false',f'guard,slot<{40-late_blocks}?0:3,false')
        sink.write_text(once(sink.read_text(),drain,drain+window),newline='\n')
        return
    if after_map:
        drain='  if(!nes_window184_drain(s->plan->window,ack))return fail(s,5);'
        sink.write_text(once(sink.read_text(),drain,drain+'''
  /* The existing long-map drain already checked the last accepted head.
   * Cover the upcoming blank while the scroll and palette are still local. */
  if(s->displayed && s->obj_next>=16){
   for(unsigned slot=0;slot<40;slot++)
    if(!nes_cost474_pause(s->plan->ctx,s->plan->guard,0,false))return fail(s,5);
  }'''),newline='\n')
        return
    sink.write_text(once(sink.read_text(), anchor, anchor + """
 /* A dense right-page prefix plus >=512 B of issued OBJ has enough accepted
  * inactive VRAM work to use a blank. Stop publishing raw tails briefly.
  * Guard every delay. The SNES independently arbitrates head, STOP and beam. */
 if(s->plan && s->plan->window && s->displayed && s->obj_next>=16 &&
    (((uint32_t)(r->map_upload>>32))&0x7ffffu)==0x7ffffu){
  uint8_t ack[12];
  if(!nes_window184_drain(s->plan->window,ack))return fail(s,5);
  for(unsigned slot=0;slot<30;slot++)
   if(!nes_cost474_pause(s->plan->ctx,s->plan->guard,0,false))return fail(s,5);
 }
"""), newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base',type=Path)
    parser.add_argument('out',type=Path)
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--after-map',action='store_true')
    modes.add_argument('--receive',action='store_true')
    modes.add_argument('--late-receive',action='store_true')
    parser.add_argument('--late-blocks',type=int,choices=(1,2,3),default=3)
    args = parser.parse_args()
    if args.late_blocks!=3 and not args.late_receive:parser.error('--late-blocks requires --late-receive')
    prepare(args.base,args.out,args.after_map,args.receive,args.late_receive,args.late_blocks)
