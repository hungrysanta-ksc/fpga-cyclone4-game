# SPDX-License-Identifier: MIT
import guard_nes_slots312 as old
from nes_delta231 import once
s=old.TB.replace('[109:0]','[112:0]')
s=once(s,'.status270(status),', ".expected_select313(1'b0),.expected_write313(1'b0),.expected_address313(9'd0),.expected_data313(8'd0),.status270(status),")
s=once(s,'  for(i=0;i<16;i++)begin address=i;repeat(2)@(negedge clk);if(data!==packet[i])$fatal(1,"legacy view %0d",i);end\n','')
s=once(s,'for(i=16;i<n;i++)begin address=i;repeat(2)@(negedge clk);if(data!==packet[i])$fatal(1,"compact batch %0d",i);end','for(i=21;i<n;i++)begin address=i;repeat(2)@(negedge clk);if(data!==packet[i])$fatal(1,"compact batch %0d",i);end')
s=once(s,'for(i=16;i<n;i++)begin address=i;repeat(2)@(negedge clk);if(data!==packet[i])$fatal(1,"typed record %0d",i);end','for(i=20;i<n;i++)begin address=i;repeat(2)@(negedge clk);if(data!==packet[i])$fatal(1,"typed record %0d",i);end')
old.TB=s
if __name__=='__main__':old.main()
