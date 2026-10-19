# SPDX-License-Identifier: MIT
"""Execute unchanged233 linked IRQ bodies with explicit MMIO inputs.

Function-body instruction counts exclude NVIC entry/exit, wait states, priority,
exception stacking and hardware latency. No peripheral or full RUN emulation.
"""
from pathlib import Path
import argparse,json,struct
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE,ELFFile
from unicorn import UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_XPSR

class IRQ:
 def __init__(self):
  self.path=BASE/'probes/nes-runtime233/arm01/src/obj-nes-100/sd2snes.elf'
  self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
  for a,n in [(0x08000000,0x100000),(0x20000000,0x10000),(0x40000000,0x4000000),(0xe0000000,0x100000)]:self.u.mem_map(a,n)
  with self.path.open('rb') as f:
   e=ELFFile(f)
   for s in e.iter_segments():
    if s['p_type']=='PT_LOAD':self.u.mem_write(s['p_vaddr'],s.data())
   self.sy={s.name:s['st_value'] for s in e.get_section_by_name('.symtab').iter_symbols()}
  # Exact linked LDR literal of nes_diag_active (not an ambiguous static symbol).
  pc=self.sy['nes_diag_active']&~1;assert self.u.mem_read(pc,6)==bytes.fromhex('014b18787047')
  ptr=struct.unpack('<I',self.u.mem_read(((pc+4)&~3)+4,4))[0]
  assert 0x20000000<=ptr<0x20010000;self.u.mem_write(ptr,b'\x01')
  self.u.mem_write(0x42400200,struct.pack('<I',1)) # GPIOA IDR bit0: reset released
  self.u.mem_write(0x42410234,struct.pack('<I',0)) # GPIOC IDR bit13: card present
  self.count=0;self.low=0;self.mmio=[];self.u.hook_add(UC_HOOK_CODE,self.code)
  self.u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,self.memory)
 def code(self,u,a,n,_):
  if a==0x080ffff0:u.emu_stop();return
  self.count+=1;self.low=min(self.low,u.reg_read(UC_ARM_REG_SP))
 def memory(self,u,access,a,n,value,_):
  if a>=0x40000000:self.mmio.append([access,a,n,value])
 def call(self,name):
  self.count=0;self.low=0x2000f000;self.mmio=[]
  for r,v in [(UC_ARM_REG_SP,self.low),(UC_ARM_REG_LR,0x080ffff1),(UC_ARM_REG_XPSR,0x01000000)]:self.u.reg_write(r,v)
  self.u.emu_start(self.sy[name]|1,0x080ffff0,count=100000)
  assert self.u.reg_read(UC_ARM_REG_PC)==0x080ffff0,(name,self.count,hex(self.u.reg_read(UC_ARM_REG_PC)))
  return dict(handler=name,instructions=self.count,stack_bytes=0x2000f000-self.low,MMIO=self.mmio)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
 irq=IRQ();rows=[]
 for i in range(20):
  r=irq.call('SysTick_Handler');r.update(case='RUN_card_present_reset_released',iteration=i);rows.append(r)
 assert int.from_bytes(irq.u.mem_read(irq.sy['ticks'],4),'little')==20
 irq.u.mem_write(irq.sy['sd_changed'],struct.pack('<I',1));rows.append(dict(case='RUN_card_change_flag',**irq.call('SysTick_Handler')))
 assert int.from_bytes(irq.u.mem_read(irq.sy['sd_changed'],4),'little')==0
 r=irq.call('TIM2_IRQHandler');assert int.from_bytes(irq.u.mem_read(irq.sy['wokefromtimer'],4),'little')==1;rows.append(dict(case='timer_update',**r))
 result=dict(passed=True,scope=__doc__,ELF_sha256=sha(irq.path),script_sha256=sha(Path(__file__)),cases=rows,
  SysTick_period_ms=10,entry_exit_cycles=None,hardware_cycles=False,full_RUN=False,
  limits=['Stable reset and present-card RUN paths plus card-change flag only; no reset transition/NMI nesting.',
   'MMIO values are explicit test inputs; register writes are observed, no peripheral behavior is emulated.'])
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:v for k,v in result.items() if k!='cases'}));print([(r['case'],r['instructions'],r['stack_bytes']) for r in rows])

if __name__=='__main__':main()
