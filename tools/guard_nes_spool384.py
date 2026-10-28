# SPDX-License-Identifier: MIT
"""ActualM4/RTL STOP after all383 source receipts and12view reads,beforePPUDMA."""
import inspect
import guard_nes_cancel378 as old
from nes_delta231 import once


def main():
 source=inspect.getsource(old.main)
 source=once(source,"s=s.replace('PRESENT_FIRST378=907','PRESENT_FIRST378=905').replace", "s=s.replace('PRESENT_FIRST378=907','PRESENT_FIRST378=907').replace")
 source=once(source,"s=once(s,'   bank=(~display_serial373[0])&1;tok=', '   waiting_stop378=1;bank=(~display_serial373[0])&1;tok=')", "s=once(s,'  tok384=dut.flow.last_map_token;', '  waiting_stop378=1;tok384=dut.flow.last_map_token;')\n s=once(s,'ppu378[a384]=b384;', 'ppu378[a384]=b384;ppu_writes378++;')")
 source=once(source,"s=once(s,'if(PRESENT378&&f>=PRESENT_FIRST378)display_tail378();', 'if(PRESENT378&&f>=PRESENT_FIRST378)begin display_tail378();stop_return378=1;end ')", "s=once(s,'if(PRESENT378&&f>=PRESENT_FIRST378)display_spool384();', 'if(PRESENT378&&f>=PRESENT_FIRST378)begin display_spool384();stop_return378=1;end ')")
 source=source.replace('display_reads265!=12','display_reads265!=36').replace("'--last','905'","'--last','907'").replace("'+LAST=905'","'+LAST=907'").replace('view_reads=12','view_reads=36')
 source=once(source,"path.write_text(s,newline='\\n')", "s=once(s,'if(n367<0)$fatal(1,\"ARM request367\");','if(n367<0)begin if(CANCEL378&&test_abort)wait(1\\'b0);else $fatal(1,\"ARM request367\");end');path.write_text(s,newline='\\n')")
 source=once(source,"ARM=sha(d/'output.elf'),TB=sha(path)", "ARM=sha(d/'output.elf'),TB=sha(path),all_source_staged_before_STOP=True")
 ns=dict(old.__dict__);exec(compile(source,'guard-spool384','exec'),ns);ns['main']()
if __name__=='__main__':main()
