"""Replay the first OBJ-mask transition of Adventure Island IV across both display banks."""
import argparse
from pathlib import Path
import sys
from unittest.mock import patch

from prepare_nes_trial802 import PROBES
from prepare_nes_tile821 import prepare
from replay_nes_mask820 import run as collect
from test_nes_mirror822 import test as query
from replay_nes_output822 import MirrorLink
from replay_nes_tile821 import main, GameLink


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","820","824","825","826"))
    p.add_argument("temp",type=Path)
    p.add_argument("rom",type=Path)
    p.add_argument("--budget",type=Path)
    p.add_argument("--phase",type=int,choices=(1,2))
    a=p.parse_args()
    capture=a.temp/"nes-demo825-visible"
    rtl=a.temp/"nes-demo825-visible-raster"
    out=a.temp/"nes-demo825-cache"
    data=PROBES/"nes-trial825/data"
    reference=PROBES/"nes-mask820/link820b/src"
    if a.action=="prepare":
        collect(capture,a.temp/"nes-trial816-board822held",rtl)
        prepare(rtl,capture,a.rom,reference,data,groups=[("change",(1500,1504,1557,1561,1565,1569))])
        query(a.temp,out,data,a.rom,True,inputs=[(data,capture,rtl)],out=out)
    else:
        assert a.phase and a.budget
        arm=reference if a.action=="820" else PROBES/f"nes-output823/link-{a.action}/src"
        link=GameLink if a.action=="820" else MirrorLink
        with patch.object(MirrorLink,"lookup_file",out/"hits.json"),patch.object(
                sys,"argv",["replay","","","","","","825-"+a.action,str(a.budget)]):
            main(data,"change","base" if a.action=="820" else "jointmirror",a.phase,a.temp,
                 arm=arm,link_class=link)
