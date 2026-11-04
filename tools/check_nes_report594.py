"""Compare linked post-session reports at UART/FatFS boundaries on Cortex-M4."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from check_nes_supply485_arm import ARM, ELFFile, sha
from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR
from check_nes_hardware494_termination import member_offset

class Reports(ARM):
    def __init__(self,src):
        self.intercepts={}
        super().__init__(src,'normal')
        self.u.mem_map(0xe000e000,0x1000)
        self.intercepts={self.syms[k]:k for k in ('printf','f_open','f_write','f_close')}
        with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
            elf=ELFFile(f)
            sizes={s.name:s['st_size'] for s in elf.get_section_by_name('.symtab').iter_symbols()}
            self.bucket_sizes={k:sizes[k] for k in ('nes_cost471_ops','nes_cost474_waits')}
            for cu in elf.get_dwarf_info().iter_CUs():
                for d in cu.iter_DIEs():
                    name=d.attributes.get('DW_AT_name')
                    if d.tag=='DW_TAG_structure_type' and name and name.value==b'nes_run136_report' and 'DW_AT_byte_size' in d.attributes:
                        self.fields={c.attributes['DW_AT_name'].value.decode():member_offset(c)
                                     for c in d.iter_children() if c.tag=='DW_TAG_member'}
                        break
                else:continue
                break
        self.low=0x2001e000
        self.formats=set()
        self.decoder=self.syms.get("nes_report594")

    def string(self,ptr):
        return bytes(self.u.mem_read(ptr,4096)).split(b'\0',1)[0]

    def hook(self,u,at,size,user):
        if getattr(self,"measuring",False):
            self.low=min(self.low,u.reg_read(UC_ARM_REG_SP))
        if at==getattr(self,"decoder",None):
            self.formats.add(u.reg_read(UC_ARM_REG_R2))
        op=self.intercepts.get(at)
        if op:
            a,b,n,w=[u.reg_read(reg) for reg in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
            if op=='printf' and self.string(a)==b'%s':
                self.printed=self.string(b)
            if op=='f_open':
                self.path=self.string(b).decode()
            if op=='f_write':
                self.files[self.path]=bytes(u.mem_read(b,n))
                u.mem_write(w,struct.pack('<I',n))
            u.reg_write(UC_ARM_REG_R0,0)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            return
        super().hook(u,at,size,user)

    def run(self,good):
        self.printed=b''
        self.files={}
        self.call('nes_budget210_reset',[])
        self.call('nes_cost471_reset_report',[])
        run=self.data_symbols['nes_run136']
        if good:
            for name,value in [('screen_valid',1),('screen_error',0xa9),('pad_valid',1),('pad_count',16),
                               ('history_valid',1),('history_count',16)]:
                self.u.mem_write(run+self.fields[name],bytes([value]))
            self.u.mem_write(run+self.fields['pad_buttons'],bytes(range(16)))
            self.u.mem_write(run+self.fields['history'],bytes(range(192)))
            self.call('nes_cost471_begin',[])
            for i in range(12):
                self.call('nes_cost471_op',[0xd0+i,i*17,0])
            self.call('nes_cost471_end',[])
            # Exercise nonzero, high-bit and 64-bit reporting fields.
            for name,n in self.bucket_sizes.items():
                self.u.mem_write(self.data_symbols[name],bytes((i*37+9)&255 for i in range(n)))
        ptr=0x20012000
        self.u.mem_write(ptr,b'PREPARED_RESET_HELD\0' if good else b'BLOCKED_RESET_HELD\0')
        self.low=0x2001e000
        before=self.instructions
        self.measuring=True
        self.call('save_report',[ptr,int(good)])
        self.measuring=False
        cost=self.instructions-before
        stack=0x2001e000-self.low
        assert b'candidate=NES-MMC577' in self.printed
        if good:
            assert len(self.files)==2 and self.printed in self.files.values()
            assert b'ppu_history_15=' in self.printed and b'pad_15_ticks=' in self.printed
        else:assert not self.files
        n=self.call('nes_budget210_format',[ptr,6144])
        assert 0<n<6144
        budget=bytes(self.u.mem_read(ptr,n+1))
        if good:assert budget[:-1] in self.files.values()
        else:assert budget.endswith(b'cost_sampled=0\n\0')
        for cap in (0,32,n,n+1):
            self.u.mem_write(ptr+cap,b'\xad\x5a')
            ret=self.call('nes_budget210_format',[ptr,cap])
            assert ret==(n if cap==n+1 else 0xffffffff)
            assert bytes(self.u.mem_read(ptr+cap,2))==b'\xad\x5a'
        return (self.printed,self.files,budget),dict(instructions=cost,observed_stack_B=stack)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('base','arm','out'):p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args()
    old,new=Reports(a.base),Reports(a.arm)
    rows=[]
    for good in (False,True):
        orig,x=old.run(good)
        now,y=new.run(good)
        assert orig==now
        rows.append(dict(persist=good,baseline=x,candidate=y,game_report_B=len(now[0]),
                         budget_B=len(now[2])-1,game_SHA256=hashlib.sha256(now[0]).hexdigest(),
                         budget_SHA256=hashlib.sha256(now[2][:-1]).hexdigest()))
    expected=json.loads((a.arm.parent/'packing.json').read_text())['formats']
    assert len(new.formats)==expected
    result=dict(exercised_formats=len(new.formats),ELF=sha(a.arm/'obj-nes-100/sd2snes.elf'),base_ELF=sha(a.base/'obj-nes-100/sd2snes.elf'),rows=rows)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(rows)
if __name__=='__main__':main()
