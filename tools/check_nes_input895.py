"""Exercise every early STOP with the final image and MMC894's measured caller correction."""
import json
from pathlib import Path

from check_nes_block894 import FirstBlock
from check_nes_first893 import entry_stack
from check_nes_game478 import (Machine, crc, sha, UC_ARM_REG_R0, UC_ARM_REG_R1,
                               UC_ARM_REG_LR, UC_ARM_REG_PC)
from check_nes_menu533 import check
from check_nes_reset796 import replay
from prepare_nes_input895 import BASE, MODES, WORK
from prepare_nes_trial802 import PROBES

ROOT = Path(__file__).resolve().parents[1]


class InputReplay(FirstBlock):
    def __init__(self,trace,entry,fault):
        super().__init__(trace,entry,fault)
        self.sources = []

    def exchange(self,u,tx_addr,rx_addr,n):
        self.sources.append('SRAM' if 0x20000000<=tx_addr<0x20010000 else 'flash'
                            if 0x08000000<=tx_addr<0x08040000 else 'other')
        super().exchange(u,tx_addr,rx_addr,n)
        rx = bytearray(u.mem_read(rx_addr,n))
        if self.fault=='e0-crc' and self.ops[-1]==0xe0:
            rx[-1] ^= 1
        elif self.fault=='offer-length' and self.ops[-1]==0xd0:
            rx[5:7] = bytes(2)
            rx[-1] = crc(rx[1:-1],8,7,0)
        elif self.fault=='offer-crc' and self.ops[-1]==0xd0:
            rx[-1] ^= 1
        elif self.fault=='decode' and self.ops[-1]==0xd1:
            rx[1:3] = b'\xff\xff'  # Packed map before BEGIN; give it a valid wire CRC.
            rx[-2:] = crc(rx[1:-2],16,0x1021,0xffff).to_bytes(2,'big')
        else:
            return
        u.mem_write(rx_addr,bytes(rx))
        self.injected=True


def qualify():
    src = WORK/'link/src'
    trace = json.loads((PROBES/'nes-first893/adventure893.json').read_bytes())['transactions']
    nominal = 0x20010000-sum(entry_stack(src))
    delta = json.loads((ROOT/'analysis/hardware894-results.json').read_bytes())['delta_B']
    entry = nominal+delta
    candidate = Machine(src,bytes(128))
    for name,mode in MODES.items():
        candidate.u.mem_write(0x20012000,f'NES {name} 895.nh1\0'.encode())
        assert candidate.call('marker_geometry',[0x20012000])==384+mode
    checks = {}
    order = [0xe0,0xd0,0xd1,0xd2,0xd0]
    ready = [bytes.fromhex('e6000040000003')]
    runs = [('BOOT',None,0),('INIT',None,1),('OFFER',None,2),('DATA',None,3),('BLOCK',None,5),
            ('INIT','e0-crc',1),('OFFER','offer-length',2),('OFFER','offer-crc',2),
            ('OFFER','empty',2),('DATA','data',3),('DATA','decode',3),('BLOCK','token',5)]
    for mode,fault,count in runs:
        block = InputReplay(trace,entry,fault)
        row = replay(src,1,'defer',probe=MODES[mode],pre_snapshots=ready,game=block)
        assert block.ops==order[:count] and block.injected==bool(fault)
        assert row['spi'].count(0x64)==1 and row['reset_asserted'] and not row['terminal']
        assert block.low>block.static_end and block.first_write is None
        if count:
            assert block.sources==['SRAM','flash','SRAM','SRAM','flash'][:count]
            # The work area is released after STOP. Run the linked formatter
            # using unused SRAM above .bss and below the restored menu stack.
            out = (block.static_end+7)&~7
            end = 0x0803fff0
            cpu = block.cpu
            cpu.reg_write(UC_ARM_REG_R0,out)
            cpu.reg_write(UC_ARM_REG_R1,4096)
            cpu.reg_write(UC_ARM_REG_LR,end|1)
            cpu.emu_start(candidate.syms['nes_budget210_format']|1,end,count=2000000)
            size = cpu.reg_read(UC_ARM_REG_R0)
            assert cpu.reg_read(UC_ARM_REG_PC)==end and 0<size<4096
            log = cpu.mem_read(out,size).decode('ascii').splitlines()
            for op in (0xd0,0xd1,0xd2,0xe0):
                assert f'first_input_{op:02X}={block.ops.count(op)}' in log
            assert f'first_input_crc_errors={int(fault=="data")}' in log
        checks[mode+'-'+(fault or 'ok')] = dict(ops=block.ops,tx_sources=block.sources,
                stop=row['records'][-1],foreground_gap=block.low-block.static_end)
    empty = bytearray.fromhex('00d6000000000000')
    empty[-1] = crc(empty[1:-1],8,7,0)
    delayed_trace = trace[:1]+[[trace[1][0],empty.hex()]]*3+trace[1:]
    block = InputReplay(delayed_trace,entry,None)
    row = replay(src,1,'defer',probe=MODES['OFFER'],pre_snapshots=ready,game=block)
    assert block.ops==[0xe0]+[0xd0]*4 and row['records'][-1]==['PROBE_STOPPED',4,0]
    assert row['spi'].count(0x64)==1 and not row['terminal']
    checks['OFFER-delayed'] = dict(ops=block.ops,stop=row['records'][-1],tx_sources=block.sources)
    old=InputReplay(trace,entry,None)
    replay(BASE/'src',1,'defer',probe=3,pre_snapshots=ready,game=old)
    assert old.ops==order and old.sources==checks['BLOCK-ok']['tx_sources']
    report = dict(firmware=sha(src/'obj-nes-100/firmware.stm'),cases=checks,entry_sp=hex(nominal),
                  replay_entry_sp=hex(entry),markers=MODES,menu=check(src,'895','OFFER'))
    (WORK/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Verified 5 endpoints, delayed offer and 7 negative cases')


if __name__=='__main__':
    qualify()
