"""Inject faults after a real column admission, and cold-restore both canceled banks."""
import argparse
import json
from pathlib import Path

from guard_nes_output852 import run, arm_guard
from prepare_nes_column853 import PROBE
from replay_nes_column853 import run as replay


def run_arm(temp,kind,tag):
    def selected(t,clip,phase,policy,tag,dma):
        replay(t,clip,phase,True,tag,eager=not lazy)
    lazy=tag=='853e'
    return arm_guard(temp,kind,selected,'column_serial',tag)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('tag')
    p.add_argument('case',choices=('cold','base','range','length','column','damage','prefix','stop','restart','arm-stop','arm-identity'))
    a=p.parse_args()
    trial=a.temp/f'nes-tile821-demo-jointmirror-p1-{a.tag}-on'
    if a.case.startswith('arm-'):
        result=run_arm(a.temp,a.case[4:],a.tag)
    else:
        seed=trial/'guard-stop/canceled.bin' if a.case=='restart' else None
        result=run(a.temp,trial,a.case,seed,column_client=PROBE/'fast')
    (PROBE/f'{a.tag}-guard-{a.case}.json').write_text(json.dumps(result,indent=2)+'\n')
