"""Run the coupled candidate with independent map sampling at op10 retire."""
import argparse
import sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'.tools/arm259-python'))
import replay_nes_ack861 as dense
from replay_nes_column853 import run as other_scene
from nes_raw506 import once


def run(temp,phase,work,tag,clip):
    arm=work/'link-credit/src'
    client=work/'client02'
    if clip=='dense':
        original=dense.main
        def override(*args,**kw):
            adapt=kw['adapt_template']
            kw.update(client=client,client_hash=dense.sha(client/'sink165.sfc'),
                      adapt_template=lambda s:map_samples(adapt(s)))
            return original(*args,**kw)
        with patch.object(dense,'main',override):
            dense.replay(temp,855,phase,128,high=True,arm_override=arm,tag_override=tag)
    else:
        import replay_nes_column853 as runner
        original=runner.main
        def override(*args,**kw):
            adapt=kw['adapt_template']
            kw['adapt_template']=lambda s:map_samples(adapt(s))
            return original(*args,**kw)
        with patch.object(runner,'main',override):
            other_scene(temp,clip,phase,True,tag,arm=arm,client=client,budget=Path.home()/'Downloads/nes-budget-mmc855.txt')


def map_samples(s):
    s=once(s,'(pb(0)==2 or pb(0)==4 or pb(0)==9)','(pb(0)==2 or pb(0)==4 or pb(0)==10)')
    return once(s,'local n=pb(0)==9 and 1472','local n=pb(0)==10 and 1472')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('work',type=lambda s:Path(s).resolve())
    p.add_argument('tag')
    p.add_argument('clip',choices=('dense','opening','transition'))
    run(**vars(p.parse_args()))
