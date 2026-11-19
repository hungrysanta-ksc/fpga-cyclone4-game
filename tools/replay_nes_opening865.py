"""Run one final linked ARM at the MMC855 SPI calibration, with the existing 65816."""
import argparse
from pathlib import Path
from prepare_nes_trial802 import PROBES
from replay_nes_column853 import run
from replay_nes_ack861 import replay


def replay_case(temp, variant, clip, phase):
    arm=PROBES/'nes-opening865'/variant/'src'
    tag='865'+variant+'-on'
    if clip=='dense':
        replay(temp,855,phase,128,high=True,arm_override=arm,tag_override=tag)
    else:
        run(temp,clip,phase,True,tag,arm=arm,client=PROBES/'nes-column854/client-e',
            budget=Path.home()/'Downloads/nes-budget-mmc855.txt')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('variant')
    p.add_argument('clip',choices=('opening','dense','transition'))
    p.add_argument('phase',type=int,choices=(1,2))
    replay_case(**vars(p.parse_args()))
