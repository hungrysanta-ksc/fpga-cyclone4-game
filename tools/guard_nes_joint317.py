# SPDX-License-Identifier: MIT
import json,sys
from pathlib import Path
import guard_nes_response315 as old
from nes_joint317 import apply
previous=old.patch
def patch(d):previous(d);apply(d)
old.old.old.old.record305=patch
old_adapt=old.adapt
def adapt(s):
    s=old_adapt(s).replace('dut.flow.manifest_byte313==190','dut.flow.manifest_at282==190')
    return s.replace(' initial begin : result264', '''
 initial begin : terminal317
  if(GNEG>=93&&GNEG<=95)begin
   if(GNEG==95)wait(dut.core.validator.state==dut.core.validator.V_FINAL317);
   else wait(dut.core.validator.state==dut.core.validator.H_CERT&&dut.core.validator.h_count==22);
   @(negedge host_clk);injected264=1;
   if(GNEG==93)force dut.core.validator.ram_q=dut.core.validator.digest[7:0]^8'hff;
   else if(GNEG==94)begin disable bus263;bus_read=1;bus_write=1;test_abort=1;end
   else force dut.core.validator.v_all_consumed=0;
  end
 end
 initial begin : result264''')
old.adapt=adapt
old.engine.CASES.update({93:'autonomous certificate digest mismatch',94:'STOP during autonomous certificate',95:'autonomous seal requires all consumed'})
if __name__=='__main__':
    old.old.old.old.main()
    d=Path(sys.argv[sys.argv.index('--out')+1])
    log=old.run(Path('C:/altera_standard/25.1std/questa_fse/win64/vsim.exe'),
      ['-c','-sv_lib','producer263','work.joint266_tb','-gGNEG=0','+LAST=905',
       '-do','onerror {quit -code 1};run -all;quit -f'],d,'positive317',180)
    assert 'PASS JOINT266 frames=1' in log
    r=json.loads((d/'result.json').read_text());r['positive_control317']=True
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n')
