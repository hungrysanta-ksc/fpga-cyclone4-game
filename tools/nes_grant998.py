"""Attribute 907's CHR demand reads and replay an ideal no-grant-wait bound."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_page963
from nes_hdma990 import BASE, PACKED


def replay(temp, phase, ideal, early=False, companion=False):
    def wrap(parent):
        class Demand(parent):
            def next_rom(self, now):
                self.current998 = self.pending[0]
                return super().next_rom(now)

            def select(self, request):
                kind, address = self.current998
                fast = ideal and self.generation == 907 and kind == 1
                calendar = self.original_select
                def immediate(at):
                    grant, reply = calendar(at)
                    return at, at + reply - grant
                with patch.object(self, "original_select", immediate if fast else calendar):
                    grant, reply = super().select(request)
                if self.generation == 907:
                    with (self.a.out/"demand998.jsonl").open("a") as stream:
                        print(json.dumps([kind,address,request,grant,reply]),file=stream)
                return grant, reply
        if early:
            from nes_objhint998 import hint
            return hint(Demand,companion)
        return Demand
    tag = ("998pair" if companion else "998prefix") if early else ("998now" if ideal else "998addr")
    with patch.object(nes_page963,"PACKED",PACKED):
        nes_page963.simulate(temp,phase,"cold",True,BASE,True,feedback=wrap,tag=tag,edition=966)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("--ideal",action="store_true")
    p.add_argument("--early",action="store_true")
    p.add_argument("--companion",action="store_true",help="also apply the existing next-pair rule to decoded objects")
    a=p.parse_args()
    if a.ideal and (a.early or a.companion):p.error("choose one experiment")
    replay(a.temp,a.phase,a.ideal,a.early or a.companion,a.companion)
