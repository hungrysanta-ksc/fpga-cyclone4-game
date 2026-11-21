"""Schedule MMC907's immutable section-5 pair during outstanding OBJ production."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha
from prepare_nes_trial907 import PROBES, WORK as BASE
from replay_nes_peer906 import compare

WORK = PROBES / 'nes-section909'
AFTER_PALETTE = PROBES / 'nes-section909-palette'


def prepare():
    name = 'nes_native_sink165.c'
    assert sha(BASE/'link/src/obj-nes-100/firmware.stm') == 'dba9d47853d5c470a85b7041019d396bd0abf70939c14ff7751ccf2e3cbcfe74'
    source = (BASE/'link/src'/name).read_text()
    palette = ' if(!span(s,3,0,p->cgram,512))return false;\n if(!oam227(s,p->oam))return false;'
    entry = 'bool nes_sink212_seal('
    source = once(source, entry, '''static bool color_oam909(struct nes_native_sink165 *s,struct nes_native_video165 *p){
 return span(s,3,0,p->cgram,512) && oam227(s,p->oam);
}
''' + entry)
    source = once(source,' if(!reuse){\n if(!p->scroll_issued', ''' /* The scroll and padding have already been sent and there is no map
  * DMA pending from this frame. Both section-5 DATA heads are immutable.
  * Keep tile ownership and the existing per-head credit/STOP checks. */
 bool tail_first=!reuse && p->scroll_issued && p->patch_count && !r->map_upload &&
                 s->plan && !s->plan->finished;
 if(!reuse){
 if(!p->scroll_issued''')
    source = once(source, palette,' if(!tail_first && !color_oam909(s,p))return false;')
    source = once(source,' if(reuse && !send635',' if(tail_first && !color_oam909(s,p))return false;\n if(reuse && !send635')
    patch = WORK/'patch'
    patch.mkdir(parents=True,exist_ok=True)
    (patch/name).write_text(source,newline='\n')
    # Leave palette/credit service in its original place. At this boundary a
    # submitted OBJ is evidence that the producer has reached the OBJ phase.
    two=(BASE/'link/src'/name).read_text()
    two=once(two,' if(!reuse){\n if(!p->scroll_issued',' bool defer_oam=false;\n if(!reuse){\n if(!p->scroll_issued')
    two=once(two,palette,''' if(!span(s,3,0,p->cgram,512))return false;
 defer_oam=p->scroll_issued && p->patch_count && !r->map_upload && s->obj_next &&
           s->plan && !s->plan->finished;
 if(!defer_oam && !oam227(s,p->oam))return false;''')
    two=once(two,' if(reuse && !send635',' if(defer_oam && !oam227(s,p->oam))return false;\n if(reuse && !send635')
    patch = AFTER_PALETTE/'patch'
    patch.mkdir(parents=True,exist_ok=True)
    (patch/name).write_text(two,newline='\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    actions=parser.add_subparsers(dest='action',required=True)
    actions.add_parser('patch')
    replay=actions.add_parser('replay')
    replay.add_argument('temp',type=Path)
    replay.add_argument('phase',type=int,choices=(1,2))
    replay.add_argument('--cold',action='store_true')
    replay.add_argument('--after-palette',action='store_true')
    guards=actions.add_parser('guards')
    guards.add_argument('game',type=Path)
    guards.add_argument('--after-palette',action='store_true')
    args=parser.parse_args()
    if args.action=='patch':
        prepare()
    elif args.action=='guards':
        from check_nes_supply905_arm import run
        run(args.game,AFTER_PALETTE if args.after_palette else WORK,907)
    else:
        work,tag=(AFTER_PALETTE,'909b') if args.after_palette else (WORK,'909')
        compare(args.temp,args.phase,args.cold,True,edition=907,work_arm=work,run_id=tag)
