// SPDX-License-Identifier: MIT
// Observation only; source125 test clock22MHz, memory168MHz, 1ps quantization.
realtime address_launch125=-1,address_capture125=-1,data_launch125=-1,data_capture125=-1;
realtime min_address125=1e9,min_data125=1e9;
integer address_checks125=0,data_checks125=0,hold_checks125=0;
always @(posedge reset)begin address_launch125=-1;address_capture125=-1;data_launch125=-1;data_capture125=-1;end
always @(posedge clk)if(!dut.sr)begin
 if(rom_response)begin
  if(data_launch125<0 || $realtime-data_launch125<90.906)$fatal(1,"CDC125 reader data age");
  if($realtime-data_launch125<min_data125)min_data125=$realtime-data_launch125;
  data_capture125=$realtime;data_checks125++;
 end
 if(rom_request && rom_ready)begin
  if(address_capture125>=0)begin
   if($realtime-address_capture125<5.950)$fatal(1,"CDC125 reader address hold");
   hold_checks125++;
  end
  address_launch125=$realtime;
 end
end
always @(posedge mem_clk)if(!dut.mr)begin
 if(dut.state==dut.IDLE && dut.pending)begin
  if(address_launch125<0 || $realtime-address_launch125<11.902)$fatal(1,"CDC125 reader address age");
  if($realtime-address_launch125<min_address125)min_address125=$realtime-address_launch125;
  address_capture125=$realtime;address_checks125++;
 end
 if(dut.state==dut.ACTIVE && dut.remaining==1)begin
  if(data_capture125>=0)begin
   if($realtime-data_capture125<45.452)$fatal(1,"CDC125 reader data hold");
   hold_checks125++;
  end
  data_launch125=$realtime;
 end
end
