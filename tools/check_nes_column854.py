"""Exercise warm corruption, overlapping coverage, cancellation and cold reconstruction."""
import argparse
import json
from pathlib import Path

from analyze_nes_column853 import verify_partial_stop
from guard_nes_output852 import arm_guard,run
from prepare_nes_column854 import ROOT
from replay_nes_column853 import run as replay


def check(temp,variant,case):
    tag='854'+variant
    trial=temp/f'nes-tile821-demo-jointmirror-p1-{tag}-on'
    client=ROOT/f'client-{variant}'
    arm=ROOT/'link-b/src'
    if case.startswith('arm-'):
        def selected(t,clip,phase,policy,name,dma):
            replay(t,clip,phase,True,name,arm=arm,client=client)
        result=arm_guard(temp,case[4:],selected,'column_serial',tag)
    else:
        seed=trial/'guard-stop/canceled.bin' if case=='restart' else None
        result=run(temp,trial,case,seed,column_client=client)
        if case=='stop':result['partial']=verify_partial_stop(trial)
    (ROOT/f'{tag}-guard-{case}.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path);p.add_argument('variant')
    p.add_argument('case',choices=('cold','base','range','length','column','damage','prefix','stop',
                                  'restart','arm-stop','arm-identity','omitted','overlap','tail-last','late-stop'))
    a=p.parse_args()
    check(a.temp,a.variant,a.case)
