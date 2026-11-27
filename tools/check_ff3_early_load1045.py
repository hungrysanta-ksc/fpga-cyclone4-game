"""Replay OPEN and LOAD in the linked frame loop before its first display ACK."""
import argparse
import struct
import zlib
from pathlib import Path
from check_ff3_sd1043 import fat16
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_PC, UC_ARM_REG_LR
from check_ff3_menu_arm import Player


class Early(Player):
    def device(self, u, pc, size, name):
        previous = len(self.reply)
        super().device(u, pc, size, name)
        if name == 'nes_native165_bulk' and len(self.reply) > previous and self.request == 1:
            self.request = 0x20

    def stub(self, name):
        def completed(u, pc, size, tag):
            u.reg_write(UC_ARM_REG_R0, 1)
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
        address=self.sym[name]&~1
        self.u.hook_add(UC_HOOK_CODE, completed, None, address, address)


def check(src, slot, expect):
    raw=slot.read_bytes()
    magic,schema,crc,prg,num,size,serial,payload_crc,header_crc=struct.unpack_from('<9I',raw)
    assert (magic,schema,prg,num,size)==(0x5353454e,1,524288,1,21264)
    assert zlib.crc32(raw[:32])==header_crc and zlib.crc32(raw[36:])==payload_crc
    disk=fat16()
    seed=Player(src,disk,crc)
    seed.state[:]=raw[36:]
    seed.command(1);seed.command(0x10);seed.command(5)
    m=Early(src,disk,crc)
    m.request=1;m.reply=[]
    m.u.mem_write(m.sym['ticks'],struct.pack('<I',100))
    # No frame is published; service the two actual mailbox commands in the
    # final foreground loop. Replace only initialization and cost telemetry.
    for name in ('nes_runtime165_begin','nes_cost471_begin','nes_cost471_end'):
        m.stub(name)
    fn=next(n for n in m.sym if n.startswith('native_frames222'))
    m.call(fn,0x20008000,crc)
    observation=m.u.mem_read(m.sym['nes_run136']+20,1)[0]
    assert m.reply==[1,1] and m.u.mem_read(m.sym['ff3_next_slot'],1)==bytes([1])
    assert observation==expect,(observation,expect)
    if not expect:
        m.flags=3;m.cold_slot=True
        assert m.call('nes_restore_boot_battery')==1 and m.state==raw[36:] and not m.cold_slot
    print('PASS verified physical slot 1, zero display frames, first_error',observation)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('src',type=Path)
    parser.add_argument('slot',type=Path)
    parser.add_argument('expected_error',type=int,choices=[0,5])
    args=parser.parse_args()
    check(args.src,args.slot,args.expected_error)
