# SPDX-License-Identifier: MIT
"""NES344 revision2: continue bounded BG planning while early bulk waits."""
import probe_nes_record344 as previous
from nes_record344 import native as old_native
from nes_delta231 import once

def native(d):
 old_native(d);p=d/'nes_input286.inc';s=p.read_text()
 s=once(s,'if(!bg_done293()||done296)return 1;', 'if((!bg_done293()&&!prefixes344)||done296)return 1;')
 s=once(s,'input285.state==NES_NATIVE165_COMMITTED&&bg_done293()&&!done296;', 'input285.state==NES_NATIVE165_COMMITTED&&(bg_done293()||prefixes344)&&!done296;')
 p.write_text(s,newline='\n')
previous.engine.native=native
previous.engine.__file__=__file__
if __name__=='__main__':previous.engine.main()
