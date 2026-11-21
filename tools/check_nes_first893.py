"""Execute run136 through the cold frame using bounded SPI response replay."""
import argparse
import json
import re
import struct
from collections import Counter
from pathlib import Path

from check_nes_reset796 import replay
from check_nes_game478 import sha
from unicorn import UC_HOOK_BLOCK, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_SP, UC_ARM_REG_PC, UC_ARM_REG_LR


class ColdFrame:
    def __init__(self, trace, entry_sp, corrupt=False):
        self.rows = [(bytes.fromhex(t), bytes.fromhex(r)) for t,r in trace]
        self.index = 0
        self.retired = False
        self.corrupt = corrupt
        self.injected = False
        self.expected_error = 4 if corrupt else 0
        self.low = entry_sp
        self.low_pc = 0
        self.steps = 0
        self.first_write = None
        self.entry_sp = entry_sp

    def install(self,u,symbols):
        self.cpu=u
        self.systick=symbols['SysTick_Handler']
        self.ticks = symbols['ticks']
        self.static_end = symbols['__bss_end__']
        u.mem_map(0xe0001000,0x1000)
        u.mem_map(0x40000000,0x30000)
        # The boot harness already maps the GPIOB RDY bit-band page.
        u.mem_map(0x42000000,0x408000)
        u.mem_map(0x42409000,0x37000)
        def put(addr,val):
            u.mem_write(addr,struct.pack('<I',val))
        def get(addr):
            return struct.unpack('<I',u.mem_read(addr,4))[0]
        dma=0x40026400
        spi=0x40013000
        put(0x40023830,1<<22)  # DMA2 clock
        put(0x40020400,(1<<6)|(1<<10))
        put(0x40020420,0x00555000)
        put(spi+8,2)
        u.mem_write(symbols['gpio_owned'],b'\x01')
        def complete(cpu,access,address,size,value,user):
            n=get(dma+0x14)
            if n and get(spi+4)==3 and get(dma+0x10)&get(dma+0x58)&1:
                assert n==get(dma+0x5c)
                self.exchange(cpu,get(dma+0x64),get(dma+0x1c),n)
                put(dma+0x14,0)
                put(dma+0x5c,0)
                put(dma,(1<<27)|(1<<5))
        u.hook_add(UC_HOOK_MEM_READ,complete,begin=dma,end=dma+3)
        # CS and all checked DMA transitions execute. Only the timer delay
        # callback returns immediately in this transaction-order replay.
        delay=symbols['delay_us']&~1
        u.hook_add(UC_HOOK_CODE,lambda cpu,*_:cpu.reg_write(UC_ARM_REG_PC,cpu.reg_read(UC_ARM_REG_LR)),
                   begin=delay,end=delay)
        counter = 0
        def dwt(cpu,access,address,size,value,user):
            nonlocal counter
            counter += 256
            cpu.mem_write(address,struct.pack('<I',counter))
        u.hook_add(UC_HOOK_MEM_READ,dwt,begin=0xe0001004,end=0xe0001007)
        def sample(cpu,at,size,user):
            sp = cpu.reg_read(UC_ARM_REG_SP)
            if sp < self.low:
                self.low,self.low_pc = sp,at
        u.hook_add(UC_HOOK_BLOCK,sample)
        def write(cpu,access,address,size,value,user):
            sp=cpu.reg_read(UC_ARM_REG_SP)
            if sp <= address < self.static_end and self.first_write is None:
                self.first_write=dict(pc=hex(cpu.reg_read(UC_ARM_REG_PC)),sp=hex(sp),
                                      address=hex(address),bytes=size,spi_completed=self.index)
        u.hook_add(UC_HOOK_MEM_WRITE,write,begin=self.static_end-2048,end=self.static_end-1)
        def step(cpu,at,size,user):
            self.steps += 1
            if self.retired:
                cpu.mem_write(self.ticks,struct.pack('<I',6100))
        at = symbols['nes_runtime165_step'] & ~1
        u.hook_add(UC_HOOK_CODE,step,begin=at,end=at)
        io=0x2000ffe0
        u.mem_write(io,struct.pack('<6I',0,*[symbols[k]|1 for k in ('load_select','load_clock','load_mosi','load_miso','wait_us')]))
        return io,0x60000,symbols['report'],0xa58fe808

    def exchange(self,u,tx_addr,rx_addr,n):
        tx = bytes(u.mem_read(tx_addr,n))
        wanted,rx = self.rows[self.index]
        assert tx == wanted,(self.index,tx.hex(),wanted.hex())
        self.index += 1
        if not self.injected and self.corrupt and tx[0]==0xd1:
            rx=rx[:-1]+bytes([rx[-1]^1])
            self.injected=True
        u.mem_write(rx_addr,rx)
        # Service the periodic observer between transactions. Advance the
        # deadline only on the step after checked EA, never inside a packet.
        u.mem_write(self.ticks,struct.pack('<I',self.index//8+5))
        if tx[0]==0xea:
            self.retired=True
        return 1

    def result(self):
        if self.corrupt:
            assert self.injected and not self.retired
        else:
            assert self.retired and self.index==len(self.rows)
        foreground_low=self.low
        foreground_pc=self.low_pc
        # Independent high-water check. Charge an aligned, extended exception
        # frame, then run the linked periodic handler from that stack depth.
        end=0x0803fff0
        self.cpu.reg_write(UC_ARM_REG_SP,(self.low-104)&~7)
        self.cpu.reg_write(UC_ARM_REG_LR,end|1)
        self.cpu.emu_start(self.systick|1,end,count=50000)
        assert self.cpu.reg_read(UC_ARM_REG_PC)==end
        return dict(transactions=self.index, checked_retire=self.retired,
                    steps=self.steps,stack_low=hex(self.low),stack_low_PC=hex(self.low_pc),
                    foreground_low=hex(foreground_low),foreground_low_PC=hex(foreground_pc),
                    foreground_gap_bytes=foreground_low-self.static_end,
                    static_gap_bytes=self.low-self.static_end,first_stack_write_to_static=self.first_write,
                    opcodes=dict(Counter(hex(t[0]) for t,r in self.rows[:self.index])))


def entry_stack(src):
    used=[]
    for unit,caller,callee in [('main','main','nes_menu_diagnostic_run'),('nes_menu_diagnostic','nes_menu_diagnostic_run','nes_menu_sd_probe'),('nes_h1_stm32','nes_menu_sd_probe','run136')]:
        listing=(src/f'obj-nes-100/{unit}.lst').read_text(errors='replace')
        body=re.split(r'^\s*\d+\s+'+caller+r':\s*$',listing,flags=re.M)[1]
        prefix=re.split(r'\bbl\s+'+callee+r'\s*$',body,flags=re.M)[0]
        assert prefix!=body
        # GCC emits CFI remember/restore for early returns. Decode CFA at
        # the actual call instruction instead of taking the function maximum.
        cfa=0; saved=[]
        for op,n in re.findall(r'\.cfi_(def_cfa_offset|remember_state|restore_state)[ \t]*(\d*)',prefix):
            if op=='def_cfa_offset':cfa=int(n)
            elif op=='remember_state':saved.append(cfa)
            else:cfa=saved.pop()
        assert cfa>0
        used.append(cfa)
    return used


def main(trace,out,src):
    data=json.loads(trace.read_bytes())
    used=entry_stack(src)
    results={}
    for name,corrupt in [('first-display',False),('bad-first-input-crc',True)]:
        frame=ColdFrame(data['transactions'],0x20010000-sum(used),corrupt)
        row=replay(src,1,'defer',pre_snapshots=[bytes.fromhex('e6000040000003')],game=frame)
        assert not row['terminal'] and row['checkpoints']==['DISPLAY_NEXT','DISPLAY_STOPPED']
        results[name]=dict(**frame.result(),checkpoints=row['checkpoints'],STOP=row['spi'].count(0x64))
    out.write_text(json.dumps(dict(firmware=sha(src/'obj-nes-100/firmware.stm'),client=data['client'],
                                   trace_ARM=data['firmware'],caller_stack_bytes=used,trace=sha(trace),cases=results),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('src',type=Path)
    a=p.parse_args()
    main(a.trace,a.out,a.src)
