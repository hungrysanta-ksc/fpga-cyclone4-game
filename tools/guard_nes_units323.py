# SPDX-License-Identifier: MIT
"""Actual M4/RTL cancellation and invalid domain/count guards."""
import inspect
import guard_nes_owner319 as old
from nes_delta231 import once
old.CASES.update({8:'invalid domain',9:'zero unit count',10:'high unit count bits',11:'raw last granule overflow'})
def main():
    s=inspect.getsource(old.main)
    s=s.replace("default='1,2,3,4,5,6,7'","default='1,2,3,4,5,6,7,8,9,10,11'")
    s=s.replace("'.cfg','.palette','.expected'","'.cfg','.palette','.expected','.lens','.desc'")
    s=s.replace('probe_nes_owner319.py','probe_nes_units323.py')
    s=once(s,"    s=once(s,'endmodule',", "    s=once(s,'if(reset||!active263||source_fault)released312<=0;', 'if(reset||!active263||source_fault||injected319)released312<=0;')\n    s=once(s,'endmodule',")
    s=once(s,'  else $fatal(1,"unknown guard319");', '''  else if(NEG319>=8&&NEG319<=11)wait(dut.flow.state==dut.flow.CHECK&&dut.flow.data_command278);
  else $fatal(1,"unknown guard319");''')
    s=once(s,'  else force dut.flow.held=0;', '''  else if(NEG319==8)force dut.flow.active305.section=8'd2;
  else if(NEG319==9)force dut.flow.active305.span=16'd0;
  else if(NEG319==10)force dut.flow.active305.span=16'h8001;
  else if(NEG319==11)begin force dut.flow.active305.section=8'd7;force dut.flow.active305.start=16'd15;force dut.flow.active305.span=16'd2;end
  else force dut.flow.held=0;''')
    ns=dict(old.__dict__)
    exec(compile(s,'guards323','exec'),ns);ns['main']()
if __name__=='__main__':main()
