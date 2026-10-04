// PSRAM arbiter with a highest-priority byte-wide GBC SaveRAM client.
// SaveRAM byte address E00000+save_addr matches the existing FXPAK .srm path.
module rom_bus_bridge_save(input wire clk,reset,allow_write,
 input wire save_valid,save_write,input wire[16:0]save_addr,input wire[7:0]save_data,
 output wire save_ready,save_rsp_valid,output wire[7:0]save_rsp_data,
 input wire cpu_valid,input wire[21:0]cpu_addr,output wire cpu_ready,
 output wire cpu_rsp_valid,output wire[15:0]cpu_rsp_data,
 input wire mcu_valid,mcu_write,input wire[23:0]mcu_addr,input wire[7:0]mcu_data,
 output wire mcu_ready,mcu_rsp_valid,output wire[7:0]mcu_rsp_data,
 input wire bg_valid,bg_write,input wire[22:0]bg_addr,input wire[15:0]bg_data,
 output wire bg_ready,bg_rsp_valid,output wire[15:0]bg_rsp_data,
 output wire[21:0]rom_addr,output wire rom_1ce,rom_2ce,rom_oe,rom_we,rom_bhe,rom_ble,
 inout wire[15:0]rom_data);
 wire admitted_bg=bg_valid&&(!bg_write||allow_write);
 wire[23:0]save_byte_addr=24'he00000+{7'b0,save_addr};
 wire ready,rsp;wire[15:0]data;
 reg[1:0]owner;reg byte_lane_q;
 wire choose_save=save_valid;
 wire choose_cpu=!choose_save&&cpu_valid;
 wire choose_mcu=!choose_save&&!cpu_valid&&mcu_valid;
 wire choose_bg=!choose_save&&!cpu_valid&&!mcu_valid&&admitted_bg;
 wire choose_byte=choose_save||choose_mcu;
 wire[23:0]byte_addr=choose_save?save_byte_addr:mcu_addr;
 assign save_ready=ready;
 assign cpu_ready=ready&&!save_valid;
 assign mcu_ready=ready&&!save_valid&&!cpu_valid;
 assign bg_ready=ready&&!save_valid&&!cpu_valid&&!mcu_valid&&(!bg_write||allow_write);
 assign save_rsp_valid=rsp&&owner==2'd2;
 assign cpu_rsp_valid=rsp&&owner==2'd1;
 assign mcu_rsp_valid=rsp&&owner==2'd3;
 assign bg_rsp_valid=rsp&&owner==2'd0;
 assign save_rsp_data=byte_lane_q?data[15:8]:data[7:0];
 assign mcu_rsp_data=byte_lane_q?data[15:8]:data[7:0];
 assign cpu_rsp_data=data;assign bg_rsp_data=data;
 always @(posedge clk)begin
  if(reset)begin owner<=0;byte_lane_q<=0;end
  else if(ready&&(choose_save||choose_cpu||choose_mcu||choose_bg))begin
   owner<=choose_save?2'd2:choose_cpu?2'd1:choose_mcu?2'd3:2'd0;
   if(choose_byte)byte_lane_q<=byte_addr[0];
  end
 end
 psram_rw3_save memory(clk,reset,choose_save||choose_cpu||choose_mcu||choose_bg,
  choose_save?save_write:choose_cpu?1'b0:choose_mcu?mcu_write:bg_write,
  choose_byte,byte_addr[0],
  choose_byte?byte_addr[23:1]:choose_cpu?{1'b0,cpu_addr}:bg_addr,
  choose_save?{save_data,save_data}:choose_mcu?{mcu_data,mcu_data}:bg_data,ready,rsp,data,
  rom_addr,rom_1ce,rom_2ce,rom_oe,rom_we,rom_bhe,rom_ble,rom_data);
endmodule
