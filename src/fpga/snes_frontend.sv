// Combined candidate SNES register + SRAM frontend. Real pad timing and the
// PHI2 reservation contract still require board validation. No MCU loader here.
module snes_frontend(
 output wire menu_write,output wire[7:0]menu_data,input wire[7:0]menu_status,
 input wire clk,reset,phi2,input wire[23:0]snes_addr,
 input wire read_n,write_n,romsel_n,input wire[7:0]snes_data_in,
 output wire[7:0]snes_data_out,output wire databus_oe_n,databus_dir,
 output wire upload_start,read_idle,
 input wire upload_busy,upload_done,upload_page,upload_valid,upload_error,
 input wire write_valid,input wire[15:0]write_addr,write_data,input wire write_word,
 output wire write_done,writer_busy,bus_error,
 output wire[18:0]ram_addr,output wire ram_oe,ram_we,inout wire[7:0]ram_data,
 output wire[9:0]joy_update,
 output wire diag_request,input wire diag_busy,diag_valid,input wire[31:0]diag_snapshot
);
 (* async_reg="true" *)reg[1:0]reset_pipe;
 always @(posedge clk or posedge reset)
  if(reset)reset_pipe<=3;else reset_pipe<={reset_pipe[0],1'b0};
 wire local_reset=reset_pipe[1];
 wire host_write;wire[3:0]host_addr;wire[7:0]host_data,host_q,reg_data;
 wire reg_oe_n,reg_dir;
 wire grant,foreground_read,slot_error,writer_error;
 wire[18:0]foreground_addr,raw_addr;wire[7:0]foreground_data;
 wire raw_register,raw_frame,raw_program;
 reg have_snapshot;
 wire locked=upload_busy||upload_start||!have_snapshot;
 assign bus_error=upload_error||slot_error||writer_error;
 always @(posedge clk or posedge local_reset)begin
  if(local_reset)have_snapshot<=0;
  else begin
   if(upload_done)have_snapshot<=1;
   if(host_write&&host_addr==1&&host_data[0])have_snapshot<=0;
  end
 end
 snes_regs_pin_bridge bridge(clk,local_reset,snes_addr,read_n,write_n,snes_data_in,
 reg_data,reg_oe_n,reg_dir,host_write,host_addr,host_data,host_q);
 wire[7:0]base_q;
 assign menu_write=host_write&&host_addr==13;assign menu_data=host_data;
 assign diag_request=host_write&&host_addr==8;
 assign host_q=host_addr==13?menu_status:host_addr==7?8'haf:
               host_addr==8?{6'b0,diag_valid,diag_busy}:
               host_addr==9?diag_snapshot[7:0]:
               host_addr==10?diag_snapshot[15:8]:
               host_addr==11?diag_snapshot[23:16]:
               host_addr==12?diag_snapshot[31:24]:base_q;
 snes_upload_regs registers(clk,local_reset,host_write,host_addr,host_data,base_q,
 upload_start,upload_busy,upload_done,upload_page,upload_valid,bus_error,joy_update);
 snes_cart_map raw_map(snes_addr,romsel_n,upload_page,raw_register,raw_frame,raw_program,raw_addr);
 snes_sram_slots slots(clk,local_reset,phi2,snes_addr,read_n,write_n,romsel_n,
 upload_page,upload_valid,locked,writer_busy,grant,foreground_read,foreground_addr,slot_error);
 sram_burst_writer writer(clk,reset,grant,foreground_read,write_valid,write_addr,
 write_data,write_word,write_done,writer_busy,writer_error,foreground_addr,foreground_data,
 ram_addr,ram_oe,ram_we,ram_data);
 // Only drive a matching, settled SRAM read. A new address resets the age;
 // raw /RD deassertion releases the SNES transceiver without CDC latency.
 reg[18:0]read_address;reg[2:0]read_age;
 always @(posedge clk or posedge local_reset)begin
  if(local_reset)begin read_age<=0;read_address<=0;end
  else if(!foreground_read||writer_busy)read_age<=0;
  else begin
   read_address<=foreground_addr;
   if(read_age==0||read_address!=foreground_addr)read_age<=1;
   else if(read_age!=7)read_age<=read_age+1'b1;
  end
 end
 // local_reset asserts asynchronously and releases on this bus clock. Do not
 // bypass it with source-domain reset in the data/OE mux: that reintroduces a
 // source-clock-to-bus-clock combinational release path.
 wire memory_drive=!local_reset&&!bus_error&&!read_n&&write_n&&
  (raw_program||(raw_frame&&upload_valid&&!locked))&&
  foreground_read&&!writer_busy&&read_age==7&&read_address==raw_addr&&foreground_addr==raw_addr;
 // Select data by address; validity belongs to OE/DIR. Feeding the entire
 // settled-read predicate through every data bit adds unnecessary mux delay.
 // Data on a disabled transceiver is unspecified and must not be consumed.
 assign snes_data_out=raw_register?reg_data:foreground_data;
 assign databus_dir=!local_reset&&(reg_dir||memory_drive);
 assign databus_oe_n=local_reset||(!memory_drive&&reg_oe_n);
 assign read_idle=!writer_busy&&!foreground_read&&(read_n||!(raw_frame||raw_program));
endmodule

