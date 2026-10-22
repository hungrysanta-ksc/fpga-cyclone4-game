# SPDX-License-Identifier: MIT
"""Run resumable work before WFI using the last checked phase snapshot."""
from nes_slice302b import native as previous
from nes_delta231 import once


def native(d):
    previous(d)
    p=d/'nes_output264.c';s=p.read_text()
    s=once(s,'unsigned plan_cache282,plan_flags282,plan_accepted282;', 'unsigned plan_cache282,plan_flags282,plan_accepted282;\nstatic unsigned phase_ready302;')
    s=once(s,'state259.retired=r;status259[7]=p[7];','state259.retired=r;status259[7]=p[7];phase_ready302=p[7];')
    s=s.replace('if(status259[7]&2)return 0;', 'if(phase_ready302&2)return 0;').replace('!(status259[7]&wait_reason302)', '!(phase_ready302&wait_reason302)')
    s=once(s,'state259.sent++;state259.sequence++;status259[7]=0;', 'state259.sent++;state259.sequence++;status259[7]=0;phase_ready302=0;')
    # Reset cannot leave a previous namespace's checked phase cached.
    s=once(s,'void reset259(void){', 'void reset259(void){phase_ready302=0;')
    p.write_text(s,newline='\n')
    p=d/'nes_refill267.c';s=p.read_text()
    loop='''  for(unsigned slices302=0;slices302<2048&&pending302()&&!progress302();slices302++){
   if(!service296()){plan_error267=5;return 0;}
   plan_bytes267=output_size285>plan_bytes267?output_size285:plan_bytes267;
  }'''
    s=once(s,'static int poll267(void){', 'static int work302(void){\n if(work_pending302()){\n'+loop+'\n }return 1;\n}\nstatic int poll267(void){')
    s=once(s,' if(plan_error267)return 0;', ' if(plan_error267)return 0;\n if(p[0]==0xe2&&!prefill_active287&&!work302())return 0;')
    # The new helper contains a second copy, so replace the complete post-response block.
    s=once(s,' if(command==0xe2&&!prefill_active287&&work_pending302()){\n'+loop+'\n }', ' if(command==0xe2&&!prefill_active287&&!work302())return 0;')
    p.write_text(s,newline='\n')
