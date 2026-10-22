# SPDX-License-Identifier: MIT
"""Native ordinary/manifest production on M4; fixture command memory poisoned."""
import inspect,shutil
import probe_nes_live287 as previous
from nes_delta231 import ROOT,sha
from nes_native289 import prepare as native


def build_rom(d):
    source=inspect.getsource(previous.build_rom)
    anchor="    arm=BASE/'.tools/arm-gnu-toolchain"
    at=source.index(anchor);source=source[:at]+"    native(d);sources.append('nes_native289.c')\n"+source[at:]
    ns=dict(previous.__dict__);ns['native']=native
    exec(compile(source,'build-live289','exec'),ns);ns['build_rom'](d)


def prepare(*args,**kwargs):
    src,pins=previous.prepare(*args,**kwargs);d=args[0]
    for n in ('nes_native289.py','nes_native289.inc','probe_nes_live289.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins


def worker(*args,**kwargs):
    s=inspect.getsource(previous.worker)
    s=s.replace('arm.uc.mem_write(0x20010000,blob)',"arm.uc.mem_write(0x20010000,b'\\xa5'*len(blob))")
    ns=dict(previous.__dict__);exec(compile(s,'worker289','exec'),ns);return ns['worker'](*args,**kwargs)


def main():
    ns=dict(previous.prior.__dict__)
    ns.update(prepare=prepare,build_rom=build_rom,worker=worker,__file__=__file__,__doc__=__doc__)
    exec(compile(inspect.getsource(previous.prior.main),'live289-main','exec'),ns);ns['main']()


if __name__=='__main__':main()
