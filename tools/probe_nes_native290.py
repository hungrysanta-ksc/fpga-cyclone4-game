# SPDX-License-Identifier: MIT
"""71 actual M4 incremental outputs with intercepted dispatch and STOP guards."""
import inspect
import probe_nes_native289 as old
from nes_delta231 import once


def main():
    s=inspect.getsource(old.main)
    s=once(s,"        for _ in range(34):", "        at=len(arm.packets);before=arm.instructions\n        assert arm.call('begin_native290',[])\n        early=0\n        for _ in range(34):")
    s=once(s,"            if ok==2:break", "            assert arm.call('tiles290',[0])\n            if ok!=2:early=len(arm.packets)-at\n            if ok==2:break")
    s=once(s,'        at=len(arm.packets);snap=save()', '        snap=save()')
    s=s.replace("arm.call('produce289',[])","arm.call('tiles290',[1])")
    s=once(s,'        before=arm.instructions\n        assert', '        before=arm.instructions\n        assert')
    s=once(s,'producer_instructions=cost,fixture_reads=', 'final_producer_instructions=cost,early_packets=early,fixture_reads=')
    ns=dict(old.__dict__);ns.update(__file__=__file__,__doc__=__doc__)
    exec(compile(s,'native290','exec'),ns);ns['main']()


if __name__=='__main__':main()
