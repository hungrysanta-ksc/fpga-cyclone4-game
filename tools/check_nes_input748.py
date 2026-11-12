# SPDX-License-Identifier: MIT
"""Exercise the linked seal with one map opportunity and a distinct OAM receipt."""
import argparse
import json
from pathlib import Path

from check_nes_deadline719 import Deadline
from check_nes_game478 import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2
from nes_raw506 import sha


def check(arm, case):
    class Probe(Deadline):
        stop_guard = 0x0807ff88

        def hook(self, u, pc, size, ctx):
            def finish(ok):
                u.reg_write(UC_ARM_REG_R0, int(ok))
                u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
            if pc == self.stop_guard:
                self.order.append('guard')
                return finish(case != 'map_stop')
            if pc == self.syms['nes_window184_drain']:
                self.order.append('OAM_receipt' if self.heads else 'map_receipt')
                return finish(case != ('OAM_fault' if self.heads else 'map_fault'))
            if pc == self.guard:
                assert u.reg_read(UC_ARM_REG_R2) == 4
                self.order.append('input')
                return finish(case != 'input_stop')
            if pc == self.callback:
                head = bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1), 10))
                self.order.append(f'E1/{head[0]}/{head[1]}')
                if head[1] == 4:
                    u.mem_write(self.window719+self.layout['nes_sink_window184']['last'],
                                head if case != 'wrong_owner' else bytes(10))
            return super().hook(u, pc, size, ctx)

    m = Probe(arm, 'normal')
    sink = m.test_sink = 0x20015800
    plan = 0x20016300
    window = m.window719 = 0x20016b00
    m.clock719 = 10_000_000
    m.heads, m.order = [], []
    def fields(address, kind, values):
        for name, value, width in values:
            m.put(address, kind, name, value, width)
    m.u.mem_write(m.data_symbols['nes_cost471_available'], (1).to_bytes(4, 'little'))
    fields(sink, 'nes_native_sink165', [('serial',48,4),('generation',952,2),('displayed',1,1),
           ('state',1,1),('plan',plan,4),('map_next',64,1),('enqueue',m.callback|1,4),
           ('exchange',m.callback|1,4),('ack635',45|(46<<32),8),('ack_clock719',m.clock719-(2795400-200000),4)])
    fields(m.resident,'nes_resident211',[('serial',48,4),('generation',952,2),('displayed',1,1),
           ('target',1,1),('prepared',1,1),('open',1,1)])
    fields(m.video,'nes_native_video165',[('valid',1,1),('generation',952,2),('bg_count',1,2),
           ('obj_count',16,2),('hdma_size',21,2),('display_mask',0x1e,1)])
    fields(plan,'nes_plan200',[('window',window,4),('guard',m.stop_guard|1,4),('bank_history',2,1),('bulk_valid',1,1)])
    m.u.mem_write(plan+m.layout['nes_plan200']['bulk'], bytes((1,0,48 if case!='other_BG' else 32,0))+bytes(8))
    fields(window,'nes_sink_window184',[('wait',m.guard|1,4),('guard',m.stop_guard|1,4),
           ('poll_limit',1,4),('status_flags',2,1)])
    m.u.mem_write(window+m.layout['nes_sink_window184']['last'], bytes((2,2))+bytes(8))
    if case=='full_OAM':
        m.u.mem_write(m.video+m.layout['nes_native_video165']['cgram'], bytes([1]))
    ok = bool(m.call('nes_sink212_seal',[sink,m.video,m.resident,4192]))
    assert ok == (case in ('normal','full_OAM','other_BG')), (case,m.order)
    assert ('E1/3/0' in m.order) == ok
    if case in ('normal','full_OAM','input_stop'):
        i=m.order.index('OAM_receipt')
        assert m.order[:2]==['map_receipt','guard'] and m.order[i+1]=='input'
        assert m.order[i-1].endswith('/4') and m.order.count('input')==1
    if case in ('map_stop','map_fault','wrong_owner','OAM_fault'):assert 'input' not in m.order
    if case=='other_BG':assert m.order[:2]==['map_receipt','input'] and 'OAM_receipt' not in m.order
    return dict(case=case,ok=ok,events=m.order)


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--arm',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    cases=('normal','full_OAM','other_BG','map_stop','map_fault','wrong_owner','OAM_fault','input_stop')
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),
                                     cases=[check(a.arm,c) for c in cases]),indent=2)+'\n')
