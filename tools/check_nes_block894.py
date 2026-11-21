"""Qualify the bounded first-block probe on the final ARM image."""
import json
import struct

from check_nes_first893 import ColdFrame, entry_stack
from check_nes_game478 import crc, sha
from check_nes_menu533 import check
from check_nes_reset796 import replay
from prepare_nes_block894 import BASE, WORK


class FirstBlock(ColdFrame):
    def __init__(self, trace, entry_sp, fault):
        super().__init__(trace, entry_sp, corrupt=fault=='data')
        self.expected_error = 4 if fault else 0
        self.fault = fault
        self.ops = []

    def exchange(self, u, tx_addr, rx_addr, n):
        op = u.mem_read(tx_addr, 1)[0]
        self.ops.append(op)
        super().exchange(u, tx_addr, rx_addr, n)
        if self.fault=='empty' and op==0xd0:
            status = bytearray.fromhex('00d6000000000000')
            u.mem_write(self.ticks, struct.pack('<I', 510))
        elif self.fault=='token' and self.ops[-2:]==[0xd2,0xd0]:
            status = bytearray(u.mem_read(rx_addr,n))
            status[4] -= 1
        else:
            return
        status[7] = crc(status[1:7],8,7,0)
        u.mem_write(rx_addr, bytes(status))
        self.injected = True


def qualify():
    src = WORK/'linkB/src'
    trace = json.loads((BASE.parent/'adventure893.json').read_bytes())
    entry = 0x20010000-sum(entry_stack(src))
    checks = {}
    for fault, ops in [(None,[0xe0,0xd0,0xd1,0xd2,0xd0]),('data',[0xe0,0xd0,0xd1]),
                       ('token',[0xe0,0xd0,0xd1,0xd2,0xd0]),('empty',[0xe0,0xd0])]:
        block = FirstBlock(trace['transactions'],entry,fault)
        row = replay(src,1,'defer',probe=3,pre_snapshots=[bytes.fromhex('e6000040000003')],game=block)
        assert block.ops==ops and block.injected==bool(fault) and not block.retired
        assert block.first_write is None and block.low>block.static_end
        assert not row['terminal'] and row['spi'].count(0x64)==1
        checks[fault or 'normal'] = dict(ops=ops,records=row['records'],stop=True,
                                          foreground_stack_gap=block.low-block.static_end)
    menu = check(src,'894','BLOCK')
    boot = replay(src,1,'defer',probe=2,pre_snapshots=[bytes.fromhex('e6000040000003')])
    assert boot['records'][-1]==['PROBE_STOPPED',2,0] and boot['frame_entry']==0
    out = dict(firmware=sha(src/'obj-nes-100/firmware.stm'),entry_sp=hex(entry),
               cases=checks,menu=menu,boot=boot['records'])
    (WORK/'checks.json').write_text(json.dumps(out,indent=2)+'\n')
    print('PASS normal, bad D1 CRC, stale D2 retirement, no input, BOOT and menu')


if __name__=='__main__':
    qualify()
