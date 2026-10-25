# SPDX-License-Identifier: MIT
"""Fill the existing wait with bounded slices; yield on real progress GPIO."""
from nes_slice302 import native as previous
from nes_delta231 import once


def native(d):
    previous(d)
    p=d/'nes_input286.inc';s=p.read_text();s+='\nunsigned pending302(void){return input285.state==NES_NATIVE165_COMMITTED&&bg_done293()&&!done296;}\n';p.write_text(s,newline='\n')
    p=d/'nes_irq284.c';s=p.read_text();s+='\n__attribute__((noinline)) unsigned progress302(void){return REG(0x40020410)&PIN;}\n';p.write_text(s,newline='\n')
    p=d/'nes_refill267.c';s=p.read_text();s=once(s,'extern unsigned service296(void),work_pending302(void);','extern unsigned service296(void),work_pending302(void),pending302(void),progress302(void);')
    s=once(s,'  if(!service296()){plan_error267=5;return 0;}\n  plan_bytes267=output_size285>plan_bytes267?output_size285:plan_bytes267;', '''  for(unsigned slices302=0;slices302<2048&&pending302()&&!progress302();slices302++){
   if(!service296()){plan_error267=5;return 0;}
   plan_bytes267=output_size285>plan_bytes267?output_size285:plan_bytes267;
  }''')
    p.write_text(s,newline='\n')
