# SPDX-License-Identifier: MIT
"""Run success, pre-frame failure and success on the same linked M4 memory."""
import argparse
import json
from pathlib import Path
from check_nes_supply485_arm import ARM, sha


def lifecycle(src, patched):
    m=ARM(src,'normal')
    m.u.mem_map(0xe000e000,0x1000)
    buf=0x20012000
    def entry():
        m.call('nes_budget210_reset',[])
        if patched:m.call('nes_cost471_reset_report',[])
    def report():
        n=m.call('nes_budget210_format',[buf,6144])
        assert 0<n<6144
        return bytes(m.u.mem_read(buf,n)).decode().splitlines()
    def frame(calls):
        m.call('nes_cost471_begin',[])
        for _ in range(calls):m.call('nes_cost471_phase',[2,0])
        m.call('nes_cost471_end',[])
    entry()
    frame(3)
    good=report()
    assert any(x.startswith('cost_phase_02=3,') for x in good)
    entry()
    failed=report()
    if patched:
        assert failed[-1]=='cost_sampled=0' and sum(x.startswith('cost_') for x in failed)==1
        assert m.call('nes_cost471_append',[buf,15,0])==0xffffffff
    else:
        assert any(x.startswith('cost_phase_02=3,') for x in failed)
    entry()
    frame(1)
    last=report()
    assert any(x.startswith('cost_phase_02=1,') for x in last)
    return dict(firmware=sha(src/'obj-nes-100/firmware.stm'),old_phase_calls_visible_after_failure=0 if patched else 3,
                next_success_calls=1,flash_B=(src/'obj-nes-100/firmware.stm').stat().st_size)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','arm','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(dict(before=lifecycle(a.base,False),after=lifecycle(a.arm,True)),indent=2)+'\n')
