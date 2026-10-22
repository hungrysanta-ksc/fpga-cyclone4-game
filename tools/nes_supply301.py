# SPDX-License-Identifier: MIT
"""Do OBJ work only after publishing BG-close and submitting a BG DMA."""
from nes_wait296 import prepare
from nes_delta231 import once


def native(d):
    prepare(d)
    p=d/'nes_input286.inc';s=p.read_text()
    s=once(s,'static unsigned done296;', 'unsigned bg_published301,bg_dma301;\nstatic unsigned done296;')
    s=s.replace('done296=0;', 'done296=0;bg_published301=bg_dma301=0;')
    s=once(s,'if(!bg_done293()||done296)return 1;', 'if(!bg_done293()||done296||!bg_published301||!bg_dma301)return 1;')
    p.write_text(s,newline='\n')
    p=d/'nes_refill267.c';s=p.read_text()
    s=once(s,'extern unsigned service296(void);', 'extern unsigned service296(void);\nextern unsigned bg_published301;')
    s=once(s,'plan_at267+=len+3;plan_sent267++;', 'plan_at267+=len+3;plan_sent267++;\n  if(len==3&&count==1&&q[3]==0x87)bg_published301=1;')
    p.write_text(s,newline='\n')
    p=d/'nes_output264.c';s=p.read_text()
    s=once(s,'static unsigned send(unsigned n){', 'extern unsigned bg_dma301,service296(void);\nstatic unsigned send(unsigned n){')
    s=once(s,' if(!io259(wire259,n+3))return fail(1);', ' unsigned bg301=wire259[1]==7&&wire259[2]==0;\n if(!io259(wire259,n+3))return fail(1);')
    s=once(s,'state259.sent++;state259.sequence++;status259[7]=0;return 1;', 'state259.sent++;state259.sequence++;status259[7]=0;\n if(bg301){bg_dma301=1;if(!service296())return fail(23);}\n return 1;')
    p.write_text(s,newline='\n')
