"""Move the guarded MMC897 OAM reuse command before the two section-5 tail packets."""
import argparse
from pathlib import Path

from compare_nes_latency898 import replay
from nes_raw506 import once
from prepare_nes_trial802 import PROBES

BASE = PROBES/'nes-sram897/link'
WORK = PROBES/'nes-oam899'
NAME = 'nes_native_sink165.c'
TAG = '899g-oam'


def prepare():
    s = (BASE/'src'/NAME).read_text()
    s = once(s, '  offset+=prefix;',
             '  if(reuse && !send635(s,p,r->target))return false;\n  offset+=prefix;')
    s = once(s, ''' }
 /* Both immutable section-5 heads may use the queue while the tile
  * producer finishes. Reuse still requires the original target-bank check. */
 if(reuse && !send635(s,p,r->target))return false;''',
             ' }else if(reuse && !send635(s,p,r->target))return false;')
    dest = WORK/'patch-g'
    dest.mkdir(parents=True, exist_ok=True)
    (dest/NAME).write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay'))
    p.add_argument('--temp',type=Path)
    p.add_argument('--clip',choices=('early','late'))
    p.add_argument('--phase',type=int,choices=(1,2))
    a=p.parse_args()
    if a.action=='prepare':
        prepare()
    else:
        replay(a.temp,a.temp/'nes-latency898',897,a.clip,a.phase,candidate_arm=WORK/'link-g/src',
               replay_tag=TAG)
