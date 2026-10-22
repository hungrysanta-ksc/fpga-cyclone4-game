# SPDX-License-Identifier: MIT
"""Retain29 transport guards; add H2/display semantics and phase-RAM STOP."""
import inspect
import guard_nes_joint265 as old
from probe_nes_joint266 import prepare
from nes_delta231 import once


def main():
 s=inspect.getsource(old.main).replace('joint265_tb','joint266_tb').replace('PASS DIRECT265','PASS DIRECT266')
 s=s.replace('GNEG==23&&j==23','GNEG==23&&j==11').replace('range(1,30)','range(1,39)')
 s=once(s,'       if(GNEG==5&&', '''       if(all263[at]==15)begin
        if((GNEG==30&&j==34)||(GNEG==31&&j==38)||(GNEG==32&&j==26)||
           (GNEG==33&&j==36)||(GNEG==34&&j==32)||(GNEG==35&&j==16))begin
         tx[j+1]=tx[j+1]^1;injected264=1;
        end
        if(GNEG==36&&j==19)begin tx[j+1]=8'h20;injected264=1;end
       end
       if(GNEG==5&&''')
 s=once(s,'  if(GNEG==3||GNEG==4)begin', '''  if(GNEG==37||GNEG==38)begin
   wait(dut.core.encoder.state==dut.core.encoder.D_CHECK&&dut.core.encoder.rec_i==13);
   @(negedge clk);disable bus263;bus_read=1;bus_write=1;
   if(GNEG==37)test_abort=1;else begin
    bus_address=24'h006070;bus_read=0;#400;bus_read=1;
   end
  end
  if(GNEG==3||GNEG==4)begin''')
 ns=dict(old.__dict__);ns.update(prepare=prepare,__file__=__file__)
 exec(compile(s,'guard266-derived','exec'),ns);ns['main']()


if __name__=='__main__':main()
