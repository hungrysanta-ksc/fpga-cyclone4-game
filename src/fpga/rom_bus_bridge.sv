// A single outstanding transaction, CPU priority at admission boundaries.
// Responses must retain the owner of the accepted request, not live priority.
module rom_bus_bridge(input wire clk,reset,allow_write,
 input wire cpu_valid,input wire[21:0]cpu_addr,output wire cpu_ready,
 output wire cpu_rsp_valid,output wire[15:0]cpu_rsp_data,
 input wire bg_valid,bg_write,input wire[22:0]bg_addr,input wire[15:0]bg_data,
 output wire bg_ready,bg_rsp_valid,output wire[15:0]bg_rsp_data,
 output wire[21:0]rom_addr,output wire rom_1ce,rom_2ce,rom_oe,rom_we,rom_bhe,rom_ble,
 inout wire[15:0]rom_data);
 wire admitted_bg=bg_valid&&(!bg_write||allow_write);
 wire ready,rsp;wire[15:0]data;reg owner_cpu;
 assign cpu_ready=ready;
 assign bg_ready=ready&&!cpu_valid&&(!bg_write||allow_write);
 assign cpu_rsp_valid=rsp&&owner_cpu;
 assign bg_rsp_valid=rsp&&!owner_cpu;
 assign cpu_rsp_data=data;assign bg_rsp_data=data;
 always @(posedge clk)begin
  if(reset)owner_cpu<=0;
  else if(ready&&(cpu_valid||admitted_bg))owner_cpu<=cpu_valid;
 end
 psram_rw3 memory(clk,reset,cpu_valid||admitted_bg,cpu_valid?1'b0:bg_write,
 cpu_valid?{1'b0,cpu_addr}:bg_addr,bg_data,ready,rsp,data,
 rom_addr,rom_1ce,rom_2ce,rom_oe,rom_we,rom_bhe,rom_ble,rom_data);
endmodule
