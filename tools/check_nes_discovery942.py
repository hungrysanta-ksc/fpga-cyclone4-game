"""Bind boot, checked STOP/menu and both DMA priority edges to a 942 final link."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import analyze_nes_obj923 as obj
import check_nes_chain935 as edge
import check_nes_decode940 as decoder
import check_nes_order938 as dispatch
import nes_obj923
import nes_return920
import analyze_nes_chain935 as chain
from nes_discovery942 import MODES, ROM, work


def check(temp,mode,*,tag=None,record='safety942.json'):
    trial=work(mode)
    tag=tag or '942'+mode
    with patch.object(nes_return920,'client',lambda _:ROM),patch.object(nes_obj923,'client',lambda _:ROM):
        nes_return920.guards(temp,'first',tag=tag,destination=trial/'final-guards.json')
        nes_obj923.obj_stops(temp,'first',tag=tag,destination=trial/'final-stops.json')
    with patch.object(obj,'client',lambda _:ROM):
        result=obj.recovery('final',trial,trial=trial)
    with patch.object(dispatch,'work',work),patch.object(decoder,'work',work):
        dispatch.run(mode)
        decoder.check(mode)
    result['edge']={}
    with patch.object(edge,'output',lambda _:ROM),patch.object(chain,'output',lambda _:ROM):
        for phase in (1,2):
            timing=chain.measure(temp,'bounded',phase,'cold',tag=tag,trial=trial)
            if not timing['tail_grant']:
                result['edge'][str(phase)]='32B grant absent'
                continue
            for case in ('head','stop'):
                result['edge'][f'{phase}-{case}']=edge.run(temp,'bounded',phase,case,tag=tag)
    (trial/record).write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('mode',choices=MODES)
    args=p.parse_args()
    check(args.temp,args.mode)
