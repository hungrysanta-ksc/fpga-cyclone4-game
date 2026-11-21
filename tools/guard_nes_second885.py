"""Inject STOP and a bad CRC in the 963 second block using the linked receiver."""
import argparse
import json
from pathlib import Path

from check_nes_game478 import crc
from guard_nes_progress870 import (
    Machine, offsets, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)


class SecondBlock(Machine):
    tick = 0x0807ffa0
    service = 0x0807ffa8

    def hook(self,u,pc,size,user):
        if pc in (self.tick,self.service):
            stop = {'before':[], 'after_read':[0xd1], 'after_pop':[0xd1,0xd2]}
            stopped = self.case in stop and self.bus == stop[self.case]
            u.reg_write(UC_ARM_REG_R0,int(pc == self.service and not stopped))
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            return
        if pc == self.spi:
            op = u.mem_read(u.reg_read(UC_ARM_REG_R1),1)[0]
            response = u.reg_read(UC_ARM_REG_R2)
            self.bus.append(op)
            super().hook(u,pc,size,user)
            if self.case == 'crc' and op == 0xd1:
                byte = response+1
                u.mem_write(byte,bytes([u.mem_read(byte,1)[0]^1]))
            if self.case == 'stale_pop' and op == 0xd0:
                status = bytearray(u.mem_read(response,8))
                status[3:5] = (self.start_token+self.index-1).to_bytes(2,'big')
                status[7] = crc(status[1:7],8,7,0)
                u.mem_write(response,bytes(status))
            return
        super().hook(u,pc,size,user)


def check(src,sender):
    m = SecondBlock(src,bytes(128))
    fields = offsets(src,'nes_native_runtime165')
    rt = 0x20012000
    blocks = [bytes.fromhex(r['wire']) for r in json.loads(sender.read_bytes())['963']]
    assert [len(b) for b in blocks[:2]] == [53,28]
    def setup():
        m.case, m.bus, m.index, m.start_token, m.prepared, m.spi_calls = 'normal', [], 0, 0, False, 0
        m.packets = blocks
        m.call('nes_native165_reset',[m.state])
        m.call('nes_resident211_reset',[m.resident])
        m.u.mem_write(rt,bytes(2048))
        for field,val in dict(receiver=m.state,resident=m.resident, ticks=m.tick|1,
                              service=m.service|1,transfer=m.spi|1,limit=100000).items():
            m.u.mem_write(rt+fields[field],val.to_bytes(4,'little'))
        assert m.call('nes_native165_poll',[m.state,m.spi|1,0]) and m.state_value()==1 and m.index==1
        m.u.mem_write(rt+fields['prefetch_left'],bytes([6]))
        m.bus.clear()
    def poll(case):
        m.case = case
        ok = bool(m.call('wait634',[rt,m.service|1,4,1]))
        left = m.u.mem_read(rt+fields['prefetch_left'],1)[0]
        assert ok == (case=='normal') and left == (5 if ok else 6)
        return dict(ok=ok,bus=m.bus.copy(),left=left)
    def snapshot():
        return bytes(m.u.mem_read(m.state,m.layout['nes_native165']['size']))
    setup()
    rows = {'normal':poll('normal')}
    expected = snapshot()
    for case, sequence in (('before',[]),('crc',[0xd1]),('after_read',[0xd1]),('after_pop',[0xd1,0xd2]),
                           ('stale_pop',[0xd1,0xd2,0xd0])):
        setup()
        rows[case] = poll(case)
        assert rows[case]['bus']==sequence
        setup()
        assert poll('normal') == rows['normal'] and snapshot()==expected
    assert rows['normal']['bus']==[0xd1,0xd2,0xd0]
    return rows


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('src','sender','output'):
        parser.add_argument(key,type=Path)
    args=parser.parse_args()
    args.output.write_text(json.dumps(check(args.src,args.sender),indent=2)+'\n')
