# SPDX-License-Identifier: MIT
"""Independent receipt CRC and cancellation plus inherited ordered ACK guards."""
import json,sys,shutil
from pathlib import Path
import guard_nes_joint286 as old
from nes_joint286 import apply as identity
from nes_joint287 import apply
from nes_delta231 import once,ROOT,sha

def main():
    def patch(d):identity(d);apply(d)
    old.apply=patch
    previous=old.old.tb
    def tb(s):
        s=previous(s)
        return once(s,' initial begin : result264',''' initial begin : descriptor287
  if(GNEG==62)begin
   wait(dut.core.validator.state==dut.core.validator.V_RREAD&&!dut.core.validator.v_mapmode&&dut.core.validator.v_bit_at>=1312);
   @(negedge host_clk);injected264=1;
   force dut.core.validator.crc_mask287=0;
   wait(dut.core.validator.state==dut.core.validator.V_RWRITE);#1;
   if(dut.core.validator.v_we)$fatal(1,"receipt write without independently completed CRC");
   wait(source_fault);
   if(dut.core.validator.fault!=7)$fatal(1,"wrong CRC coverage fault");
  end
  if(GNEG==63)begin
   wait(dut.core.validator.state==dut.core.validator.V_PWRITE&&dut.core.validator.v_end283>dut.core.validator.v_bit_at+8);
   @(negedge host_clk);disable bus263;bus_read=1;bus_write=1;injected264=1;test_abort=1;
  end
 end
 initial begin : result264''')
    old.old.tb=tb
    old.old.old.CASES.update({62:'missing completed CRC suppresses receipt RAM write',63:'STOP inside complete descriptor receipt RAM walk'})
    old.main()
    d=Path(sys.argv[sys.argv.index('--out')+1]);r=json.loads((d/'result.json').read_text());r['scope287']=__doc__
    for n in ('nes_joint287.py','guard_nes_joint287.py'):shutil.copyfile(ROOT/'tools'/n,d/n);r['entry_hashes'][n]=sha(d/n)
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':main()
