# SPDX-License-Identifier: MIT
"""Receipt walker boundaries, crossing CHR/HDMA, CRC masks and cancellation."""
import guard_nes_range283 as old
from nes_delta231 import once

def main():
    s=old.TB
    s=once(s,".grant_serial278(32'd0)",".grant_serial278(32'd1)")
    s=once(s,'reg clk=0,reset=1,stop=0,valid=0,map=0;', 'reg desc=0;reg clk=0,reset=1,stop=0,valid=0,map=0;')
    s=once(s,'nes_validator278 dut(', 'nes_validator278 dut(.crc_reset287(1\'b0),.v_descriptor287(desc),')
    s=once(s,'dut.active=1;dut.state=dut.V_ACTIVE;dut.v_bank=0;writes=0;', 'dut.active=1;dut.state=dut.V_ACTIVE;dut.crc_mask287=65535;desc=0;writes=0;')
    s=once(s,'  $display("PASS RANGE283', '''  clear();desc=1;accept(1184,144,0);
  clear();desc=1;accept(1304,24,0);
  clear();desc=1;accept(1312,16,0);
  clear();desc=1;reject(1183,2,0);
  clear();desc=1;reject(1327,2,0);
  clear();desc=1;dut.crc_mask287=16'h00ff;accept(1312,8,0);
  begin integer saved_writes;saved_writes=writes;submit(1320,8,0);
   if(fault!=7||writes!=saved_writes)$fatal(1,"missing upper CRC wrote receipt");checks++;
  end
  clear();desc=1;dut.crc_mask287=16'hfffe;
  begin integer saved_writes;saved_writes=writes;submit(1312,16,0);
   if(fault!=7||writes!=saved_writes)$fatal(1,"missing first CRC wrote receipt");checks++;
  end
  $display("PASS RANGE283''')
    old.TB=s;old.main()

if __name__=='__main__':main()
