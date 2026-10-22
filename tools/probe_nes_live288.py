# SPDX-License-Identifier: MIT
"""Live planner/output with explicit extra ARM workset RAM; unchanged RTL287."""
import inspect,shutil
import probe_nes_live287 as previous
from nes_delta231 import ROOT,sha


def build_rom(d):
    source=inspect.getsource(previous.build_rom).replace('import probe_nes_planner287 as planner','import probe_nes_planner288 as planner')
    ns=dict(previous.__dict__);exec(compile(source,'build-live288','exec'),ns);ns['build_rom'](d)


def prepare(*args,**kwargs):
    src,pins=previous.prepare(*args,**kwargs);d=args[0]
    for n in ('nes_planner288.py','probe_nes_planner288.py','probe_nes_live288.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins


def main():
    ns=dict(previous.prior.__dict__)
    ns.update(prepare=prepare,build_rom=build_rom,worker=previous.worker,__file__=__file__,__doc__=__doc__)
    exec(compile(inspect.getsource(previous.prior.main),'live288-main','exec'),ns);ns['main']()


if __name__=='__main__':main()
