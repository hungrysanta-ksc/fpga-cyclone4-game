# SPDX-License-Identifier: MIT
"""Execute one pending OBJ planner step before sleeping for DMA progress."""
from nes_bg295 import prepare as previous
from nes_delta231 import once

def prepare(d):
 previous(d)
 p=d/'nes_input286.inc';s=p.read_text()
 s=once(s,'unsigned begin_step286(void){return start286();}', 'static unsigned done296;\nunsigned begin_step286(void){done296=0;return start286();}')
 s=once(s,'unsigned next_step286(void){unsigned result=step286();', 'unsigned next_step286(void){if(input285.state!=NES_NATIVE165_COMMITTED)return 0;if(done296)return 2;unsigned result=step286();')
 s=once(s,'return result;}', 'if(result==2)done296=1;return result;}')
 s=once(s,'void stop286(void){', 'void stop286(void){done296=0;')
 s+='\nunsigned service296(void){if(input285.state!=NES_NATIVE165_COMMITTED)return 0;if(!bg_done293()||done296)return 1;return next_step286()!=0;}\n'
 p.write_text(s,newline='\n')
 p=d/'nes_refill267.c';s=p.read_text()
 s=once(s,'extern unsigned prefill_active287;', 'extern unsigned prefill_active287,output_size285;\nextern unsigned service296(void);')
 s=once(s,' if(plan_error267)return 0;', ' if(plan_error267)return 0;\n if(p[0]==0xe2&&!prefill_active287){if(!service296()){plan_error267=5;return 0;}plan_bytes267=output_size285>plan_bytes267?output_size285:plan_bytes267;}')
 p.write_text(s,newline='\n')
