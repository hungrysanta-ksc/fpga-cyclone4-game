# SPDX-License-Identifier: MIT
"""Native293 command/plan order equivalence and inherited commit/STOP guards."""
import inspect
import probe_nes_native289 as old
from nes_bg293 import unbatch
from nes_delta231 import once


def main():
    s=inspect.getsource(old.main)
    s=once(s,"assert bytes(arm.uc.mem_read(arm.symbols['output285'],word('output_size285')))==(BASE/f'probes/nes-joint284/test04/plans{f-904}.bin').read_bytes()", "actual=bytes(arm.uc.mem_read(arm.symbols['output285'],word('output_size285')))\n        assert unbatch(actual)==unbatch((BASE/f'probes/nes-joint284/test04/plans{f-904}.bin').read_bytes()),('plan order293',f)\n        (d/f'plans{f-904}.bin').write_bytes(actual)")
    ns=dict(old.__dict__);ns.update(unbatch=unbatch,__file__=__file__,__doc__=__doc__)
    exec(compile(s,'native293','exec'),ns);ns['main']()


if __name__=='__main__':main()
