"""Compare the linked planners on identical controller, collector and bank histories."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from check_ff3_battle1047 import captured, replay, runtime_modes
from check_ff3_walk1048 import field_rtl

ROOT=Path(__file__).resolve().parents[1]
W=ROOT.parent/'probes/nes-ff3-1049'
SCENES=(('town','outside',703),('inn-walk','housewalk',1132),('field','outside',1018))


def compare(new, dest):
    base=W.parent/'nes-ff3-1048/link-final/src'
    runtime_modes(new,page_history=True)
    result={'scenes':{}}
    for scene,route,first in SCENES:
        log=W/(scene+'-rtl')/f'{first}.log'
        text=log.read_text(errors='replace')
        data=list(captured(log))
        masks={int(f):int(v,16) for f,v in re.findall(r'CLEAN_PAGES (\d+) ([0-9a-fA-F]{2})',text)}
        assert len(data)==len(masks)==6 and 'PASS GEOMETRY230 frames=6' in text
        assert len({geometry[2][128] for f,geometry in data})>1, (scene,'camera stationary')
        assert len({(W/route/f'{f:03}.ppm').read_bytes() for f,g in data})==6
        clean={f:m==255 for f,m in masks.items()}
        pair=[replay(src,data,clean,True,1,pages=masks,profile=True) for src in (base,new)]
        for a,b in zip(*pair,strict=True):
            for k in ('f','image','tile_bytes','commands','descriptor_bytes'):
                assert a[k]==b[k],(scene,k,a,b)
        scores=[sum(a['planner_instructions'] for a in rows) for rows in pair]
        assert scores[1]<scores[0]
        print(scene,scores)
        skipped=[replay(src,data,clean,True,2,pages=masks) for src in (base,new)]
        assert skipped[0]==skipped[1], (scene,'skipped capture')
        result['scenes'][scene]={'scores':scores,'rows':pair,'every_other_frame':len(skipped[0])}
    # A reference attack from the original board has a global dirty flag only.
    # Treat every write there as dirtying all eight pages on both ARM links.
    log=W.parent/'nes-ff3-1047/test/vsim-checkpoint.log'
    evidence=log.read_text(errors='replace')
    dirty={int(f):b=='1' for f,b in re.findall(r'CHR_HISTORY (\d+) ([01])',evidence)}
    captures=list(captured(log))
    masks={f:255 if clean else 0 for f,clean in dirty.items()}
    attack=[replay(src,captures,dirty,True,3,pages=masks,native_colors=True) for src in (base,new)]
    assert len(attack[0])>=20 and attack[0]==attack[1]
    result['battle_checked_frames']=len(attack[0])
    result['firmware']=[hashlib.sha256((src/'obj-nes-100/firmware.stm').read_bytes()).hexdigest() for src in (base,new)]
    dest.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('src',type=Path)
    ap.add_argument('report',type=Path)
    ap.add_argument('--rtl',action='store_true',help='Replay the captured routes under the licensed Questa wrapper first')
    args=ap.parse_args()
    if args.rtl:
        for scene,route,first in SCENES:
            field_rtl(W/route,W.parent/'nes-ff3-1048/board-io',W/(scene+'-rtl'),56,first,first+5)
    compare(args.src,args.report)
