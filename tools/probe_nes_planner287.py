# SPDX-License-Identifier: MIT
"""Actual M4 checked-row candidate, byte-exact plans and all material."""
import inspect,json,shutil
from pathlib import Path
import probe_nes_planner286 as old
from nes_planner287 import patch
from nes_delta231 import ROOT,sha


def build(d):
    def transform(s):
        p=d/'nes_resident211.c';p.write_text(p.read_text()+'\n'+(ROOT/'tools/nes_rows287.inc').read_text(),encoding='utf-8',newline='\n')
        return patch(old.patch(s))
    ns=dict(old.__dict__);ns['patch']=transform
    exec(compile(inspect.getsource(old.build),'build287','exec'),ns);pins=ns['build'](d)
    for n in ('nes_rows287.inc','nes_planner287.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[str(ROOT/'tools'/n)]=sha(ROOT/'tools'/n)
    return pins


def main():
    ns=dict(old.__dict__);ns.update(build=build,__file__=__file__,__doc__=__doc__)
    source=inspect.getsource(old.main).replace('stage=286','stage=287')
    source=source.replace('row=dict(frame=f,','row=dict(rows_reused287=arm.word("rows_reused287"),rows_full287=arm.word("rows_full287"),frame=f,')
    exec(compile(source,'planner287','exec'),ns);ns['main']()


if __name__=='__main__':main()
