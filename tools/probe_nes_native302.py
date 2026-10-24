# SPDX-License-Identifier: MIT
"""71 actual M4 incremental outputs with intercepted dispatch and STOP guards."""
import inspect
import probe_nes_native289 as old
from nes_delta231 import once
from nes_bg293 import unbatch
from nes_bg295 import unbatch as unbatch295


def main():
    s=inspect.getsource(old.main)
    s=once(s,"        for _ in range(34):", "        at=len(arm.packets);before=arm.instructions\n        assert arm.call('begin_native290',[])\n        early=0\n        for _ in range(34):")
    s=once(s,"            if ok==2:break", "            assert arm.call('service296',[])\n            assert arm.call('tiles290',[0])\n            if ok!=2:early=len(arm.packets)-at\n            if ok==2:break")
    s=once(s,'        at=len(arm.packets);snap=save()', '        snap=save()')
    s=s.replace("arm.call('produce289',[])","arm.call('tiles290',[1])")
    s=once(s,'        before=arm.instructions\n        assert', '        before=arm.instructions\n        assert')
    s=once(s,'producer_instructions=cost,fixture_reads=', 'final_producer_instructions=cost,early_packets=early,fixture_reads=')
    s=once(s,"assert bytes(arm.uc.mem_read(arm.symbols['output285'],word('output_size285')))==(BASE/f'probes/nes-joint284/test04/plans{f-904}.bin').read_bytes()", "actual=bytes(arm.uc.mem_read(arm.symbols['output285'],word('output_size285')))\n        assert unbatch295(actual)==unbatch((BASE/f'probes/nes-joint284/test04/plans{f-904}.bin').read_bytes())\n        (d/f'plans{f-904}.bin').write_bytes(actual)")
    s=s.replace('range(34)','range(2048)')
    ns=dict(old.__dict__);ns['unbatch']=unbatch;ns['unbatch295']=unbatch295;ns.update(__file__=__file__,__doc__=__doc__)
    exec(compile(s,'native294','exec'),ns);ns['main']()


if __name__=='__main__':main()
