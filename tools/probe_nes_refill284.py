# SPDX-License-Identifier: MIT
"""Live checked progress/PB8 EXTI/WFI, ARM refill, ROM and CPU trace schedule.

NVIC/EXTI is a bounded executable adapter, not the STM32 peripheral simulator:
real compiled handler, eight-word exception frame, PRIMASK and W1C are modeled.
24 entry/exit cycles per EXTI are explicit zero-wait allocations, not WCET.
Existing SysTick bodies and source instruction replay retain their prior scope.
"""
import inspect,json,shutil,struct,time
from pathlib import Path
import probe_nes_refill283 as prior
import probe_nes_refill267 as old
from probe_nes_arm264 import ARM as BaseARM
from unicorn import UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from nes_delta231 import BASE,ROOT,sha,once
from nes_joint284 import apply


class Live(old.Live):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.level=0;self.exception_cycles=0
    def exchange(self,tx):
        self.seq+=1;instructions=self.arm.instructions-self.before;self.before=self.arm.instructions
        irq_instructions=0
        while self.irq and self.now>=self.next_irq:
            row=self.irq.call('SysTick_Handler');row.update(due_RTL_ns=self.next_irq,service_RTL_ns=self.now)
            self.irq_rows.append(row);irq_instructions+=row['instructions'];self.next_irq+=10000000
        cycles=self.exception_cycles;self.exception_cycles=0
        p=self.d/'arm-request.tmp'
        p.write_text(f'{260 if tx is None else len(tx)} {instructions+irq_instructions} {cycles}\n'+('' if tx is None else tx.hex(' ')),encoding='ascii')
        p.rename(self.d/f'arm-req{self.seq}');p=self.d/f'arm-rsp{self.seq}';deadline=time.monotonic()+180
        while True:
            try:lines=p.read_text().splitlines();break
            except (FileNotFoundError,PermissionError):
                if time.monotonic()>deadline:raise TimeoutError(f'ARM284 request {self.seq}')
                time.sleep(.001)
        low,high,level=map(int,lines[0].split());self.now=low+(high<<32);self.level=level
        rx=bytes.fromhex(lines[1]) if tx else b''
        if tx is not None:assert len(rx)==len(tx)
        self.transfers.append(dict(tx='' if tx is None else tx.hex(),rx=rx.hex(),instructions=instructions,
            IRQ_instructions=irq_instructions,exception_cycles284=cycles,wait284=tx is None,IRQ_level284=level,RTL_ns=self.now))
        if tx and tx[0]==0xe1:self.packets.append(tx[1:-2])
        self.arm.gpio(level);return rx
    def transfer(self,tx):return self.exchange(tx)
    def wait(self):return self.exchange(None)


class ARM(BaseARM):
    def __init__(self,elf,endpoint):
        self.pending=False;self.in_handler=False;self.action=None;self.exti=[];self.mmio=[];self.pr=0
        super().__init__(elf,endpoint)
        self.uc.mem_map(0x40000000,0x4000000);self.uc.mem_map(0xe0000000,0x100000)
        self.uc.hook_add(UC_HOOK_MEM_WRITE|UC_HOOK_MEM_READ,self.memory)
    def memory(self,uc,access,address,size,value,user):
        from unicorn import UC_MEM_WRITE
        if address<0x40000000:return
        self.mmio.append((access,address,size,value))
        if address==0x40013c14:
            if access==UC_MEM_WRITE:self.pr&=~value;self.pending=bool(self.pr&256)
            else:uc.mem_write(address,struct.pack('<I',self.pr))
    def gpio(self,level):
        previous=struct.unpack('<I',self.uc.mem_read(0x40020410,4))[0]&256
        self.uc.mem_write(0x40020410,struct.pack('<I',256 if level else 0))
        if level and not previous:
            self.pr|=256;self.pending=True
    def enabled(self):
        def word(a):return int.from_bytes(self.uc.mem_read(a,4),'little')
        return (word(0xe000e100)&(1<<23)) and (word(0x40013c00)&256) and (word(0x40013c08)&256) and (word(0x40013810)&15)==1
    def hook(self,uc,address,size,user):
        opcode=bytes(uc.mem_read(address,2))
        if self.in_handler and opcode==b'\x70\x47' and uc.reg_read(UC_ARM_REG_LR)==0xfffffff9:
            self.instructions+=1;self.action='return';uc.emu_stop();return
        if not self.in_handler and self.pending and self.enabled() and not uc.reg_read(UC_ARM_REG_PRIMASK):
            self.action='irq';uc.emu_stop();return
        if opcode==b'\x30\xbf':
            assert not self.in_handler
            self.instructions+=1;self.action='wait';uc.emu_stop();return
        super().hook(uc,address,size,user)
    def call(self,name,args):
        uc=self.uc
        for r,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):uc.reg_write(r,v)
        uc.reg_write(UC_ARM_REG_SP,0x2003f000);uc.reg_write(UC_ARM_REG_LR,0x0800fff1);uc.reg_write(UC_ARM_REG_XPSR,0x01000000)
        pc=self.symbols[name]|1;context=None;entry=None
        regs=(UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R12,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_XPSR)
        for _ in range(100000):
            self.action=None;uc.emu_start(pc,0x0800fff2,count=20000000)
            pc=uc.reg_read(UC_ARM_REG_PC)
            if self.action=='wait':
                self.endpoint.wait();pc+=2
            elif self.action=='irq':
                assert context is None
                context=uc.context_save();sp=uc.reg_read(UC_ARM_REG_SP);assert sp%8==0
                frame=[uc.reg_read(r) for r in regs];uc.mem_write(sp-32,struct.pack('<8I',*frame));uc.reg_write(UC_ARM_REG_SP,sp-32)
                self.low_sp=min(self.low_sp,sp-32);uc.reg_write(UC_ARM_REG_LR,0xfffffff9);uc.reg_write(UC_ARM_REG_XPSR,0x01000027)
                self.in_handler=True;entry=dict(frame=frame,SP=sp-32,start=self.instructions,RTL_ns=self.endpoint.now)
                pc=self.symbols['EXTI9_5_IRQHandler']
            elif self.action=='return':
                assert context is not None and self.in_handler
                assert list(struct.unpack('<8I',uc.mem_read(entry['SP'],32)))==entry['frame']
                entry['instructions']=self.instructions-entry.pop('start');entry['entry_exit_cycles']=24;self.exti.append(entry)
                uc.context_restore(context);context=None;self.in_handler=False;pc=uc.reg_read(UC_ARM_REG_PC)
                self.endpoint.exception_cycles+=24
            else:
                assert pc==0x0800fff0,'ARM284 limit/fault'
                return uc.reg_read(UC_ARM_REG_R0)
            pc|=1
        raise AssertionError('ARM284 exception/wait limit')


def worker(d,last,irq=False,rom=False):
    source=inspect.getsource(old.worker)
    source=once(source,"arm.call('reset259',[]);", "arm.call('irq_init284',[]);arm.call('reset259',[]);")
    source=once(source,"IRQ_entry_exit_cycles=None,IRQ_preemption_modeled=False", "IRQ_entry_exit_cycles=24,IRQ_preemption_modeled='PB8 foreground boundaries',EXTI284=arm.exti,MMIO284=arm.mmio")
    ns=dict(old.__dict__);ns.update(Live=Live,ARM=ARM)
    # Use the exact current split-command verifier, not the obsolete264 wire oracle.
    from probe_nes_split274 import verify
    ns['verify']=verify
    exec(compile(source,'worker284','exec'),ns);return ns['worker'](d,last,irq,rom)


def prepare(*args,**kwargs):
    src,pins=prior.prepare(*args,**kwargs);d=args[0];apply(d)
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,' nes_spi270 spi_front270(', ' wire progress_irq284,progress_mode284;\n nes_spi270 spi_front270(.progress_irq284(progress_irq284),.progress_mode284(progress_mode284),')
    s=once(s,'#(delay267*CPI*1000.0/84.0);', '#((delay267*CPI+bridge267(6,0,0))*1000.0/84.0);')
    s=once(s,'     if(n267==0)finished267=1;', '''     if(n267==260)begin : irqwait284
      fork : wake284
       begin wait(progress_irq284);end
       begin #(10000000-($time%10000000));end // next periodic timer, not a poll delay
      join_any
      disable wake284;
      $fwrite(events261,"wait284,%0d,%0d,%0t,%0d,%0d\\n",f,progress_irq284,$time,delay267,bridge267(6,0,0));
     end else if(n267==0)begin
      finished267=1;$fwrite(events261,"armdone284,%0d,%0t,%0d,%0d\\n",f,$time,delay267,bridge267(6,0,0));
     end''')
    s=once(s,'"arm267,%0d,%0d,%0d,%0t,%0d\\n",f,tx[0],n267,$time,delay267',
           '"arm267,%0d,%0d,%0d,%0t,%0d,%0d\\n",f,tx[0],n267,$time,delay267,bridge267(6,0,0)')
    s=once(s,"     ignore267=bridge267(4,int'($time)","     ignore267=bridge267(7,progress_irq284,0);\n     ignore267=bridge267(4,int'($time)")
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_bridge267.c';s=p.read_text()
    s=once(s,'static unsigned serial, count, delay,', 'static unsigned extra284,level284;\nstatic unsigned serial, count, delay,')
    s=once(s,'fscanf(f,"%u %u",&count,&delay)!=2||count>259', 'fscanf(f,"%u %u %u",&count,&delay,&extra284)!=3||count>260')
    s=once(s,'for(unsigned i=0;i<count;i++)if(fscanf', 'for(unsigned i=0;i<(count==260?0:count);i++)if(fscanf')
    s=once(s,'fprintf(f,"%u %u\\n",(unsigned)a,(unsigned)b);', 'fprintf(f,"%u %u %u\\n",(unsigned)a,(unsigned)b,level284);')
    s=once(s,'for(unsigned i=0;i<count;i++)fprintf', 'for(unsigned i=0;i<(count==260?0:count);i++)fprintf')
    s=once(s,' if(op==5)return (int)delay;', ' if(op==5)return (int)delay;\n if(op==6)return (int)extra284;\n if(op==7){level284=(unsigned)a;return 0;}')
    p.write_text(s,encoding='utf-8',newline='\n')
    for n in ('nes_joint284.py','nes_refill284.c','nes_irq284.c','probe_nes_refill284.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(ROOT/'tools'/n)
    return src,pins


def build_rom(d):
    prior.build_rom(d)
    p=d/'nes_output264.c';s=p.read_text()
    s=once(s,' unsigned n=full?24:9;', ' unsigned n=full?24:12;')
    s=once(s,' if(!io259(status259,n))return fail(1);',' if(!io259(status259,n))return fail(1);\n if(!full)return !state259.error;')
    s=once(s,' batch_bytes260=0;plan_cache282=0;', ' extern unsigned wait_armed284;wait_armed284=0;\n batch_bytes260=0;plan_cache282=0;')
    # Frame ownership begins with a checked E2 before EXTI is unmasked. Failed
    # foreground execution masks the line, as does successful plan retirement.
    s=once(s,'unsigned frame259(', 'static unsigned frame_core284(')
    s+='''
extern void irq_end284(void);
unsigned frame259(const uint8_t *plan,unsigned bytes,uint32_t serial,unsigned generation){
 extern unsigned wait_armed284;
 irq_end284();plan_cache282=0;wait_armed284=0;
 unsigned ok=frame_core284(plan,bytes,serial,generation);
 if(!ok)irq_end284();return ok;
}
'''
    p.write_text(s,encoding='utf-8',newline='\n')
    shutil.copyfile(ROOT/'tools/nes_refill284.c',d/'nes_refill267.c');shutil.copyfile(ROOT/'tools/nes_irq284.c',d/'nes_irq284.c')
    arm=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
    old.run(arm/'arm-none-eabi-gcc.exe',['-std=c11','-Os','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-ffunction-sections','-fdata-sections','-fstack-usage','-fno-builtin','-nostdlib','-Wl,-T,layout.ld','-Wl,-Map,output.map','nes_output264.c','nes_refill267.c','nes_irq284.c','stubs.s','-o','output.elf'],d,'build284')
    old.run(arm/'arm-none-eabi-size.exe',['output.elf'],d,'size284')
    old.run(arm/'arm-none-eabi-objdump.exe',['-dr','output.elf'],d,'disassembly284')


def main():
    ns=dict(old.__dict__);ns.update(prepare=prepare,build=prior.prior.prior.prior.build,build_rom=build_rom,worker=worker,__file__=__file__,__doc__=__doc__)
    exec(compile(inspect.getsource(old.main),'refill284-main','exec'),ns);ns['main']()


if __name__=='__main__':main()
