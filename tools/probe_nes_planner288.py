# SPDX-License-Identifier: MIT
"""Actual M4 workset index candidate on all original plan/metadata oracles."""
import inspect,shutil
import probe_nes_planner287 as previous
import probe_nes_planner286 as old
from nes_planner288 import patch
from nes_delta231 import ROOT,sha


def build(d):
    def transform(s):return patch(previous.patch(s))
    ns=dict(previous.__dict__);ns['patch']=transform
    exec(compile(inspect.getsource(previous.build),'build288','exec'),ns)
    pins=ns['build'](d)
    for n in ('nes_planner288.py','probe_nes_planner288.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[str(ROOT/'tools'/n)]=sha(ROOT/'tools'/n)
    return pins


def main():
    ns=dict(old.__dict__);ns.update(build=build,__file__=__file__,__doc__=__doc__)
    source=inspect.getsource(old.main).replace('stage=286','stage=288')
    source=source.replace('row=dict(frame=f,','row=dict(rows_reused287=arm.word("rows_reused287"),rows_full287=arm.word("rows_full287"),frame=f,')
    exec(compile(source,'planner288','exec'),ns);ns['main']()


if __name__=='__main__':main()
