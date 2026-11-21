"""Compare checking SEAL credit every four confirmed input blocks with MMC897."""
import argparse
from pathlib import Path

from compare_nes_latency898 import replay
from nes_raw506 import once
from prepare_nes_trial802 import PROBES

WORK = PROBES / 'nes-ack902'
BASE = PROBES / 'nes-sram897/link'


def prepare():
    name = 'nes_native_runtime165.c'
    source = (BASE/'src'/name).read_text()
    source = once(source, '   if(reason!=2)break;',
                  '   if(reason!=2 || !(s->prefetch_left & 3u))break;')
    directory = WORK/'patch'
    directory.mkdir(parents=True, exist_ok=True)
    (directory/name).write_text(source, newline='\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'replay'))
    p.add_argument('--temp', type=Path)
    p.add_argument('--clip', choices=('early','late'))
    p.add_argument('--phase', type=int, choices=(1,2))
    args = p.parse_args()
    if args.action == 'prepare':
        prepare()
    else:
        replay(args.temp, args.temp/'nes-latency898', 897, args.clip, args.phase,
               candidate_arm=WORK/'link/src', replay_tag='902-credit4')
