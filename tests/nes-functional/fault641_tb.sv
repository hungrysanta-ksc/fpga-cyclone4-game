// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module fault641_tb;
 reg host=0, nes=0, reset=1;
 always #5.952 host=!host;
 reg halt_nes=0, core_error_in=0, input_error=0, sink_error=0;
 always #22.727 if(!halt_nes)nes=!nes;
 `include "spi200_bus.svh"
 reg capture_begin=0, owned=0, release_frame=0;
 reg [15:0] gen=31;
 wire lease, lease_fault, permitted, drained, retire;
 wire [15:0] captured_gen, retired_gen;
 wire [31:0] epoch;
 nes_capture_lease201 owner(.clk(nes),.reset(reset),.stop(1'b0),.capture_begin(capture_begin),
  .frame_owned(owned),.geometry_valid(owned),.frame_generation(gen),.export_release(release_frame),
  .export_error(4'd0),.source_ready(1'b1),.source_is_rom(1'b1),.source_writing(1'b0),.live_epoch(32'd1),
  .reader_drained(drained),.retire_commit(retire),.retire_generation(retired_gen),.lease_valid(lease),
  .retire_permitted(permitted),.captured_epoch(epoch),.captured_generation(captured_gen),.fault(lease_fault),
  .waiting_display(),.release_frame(),.export_permitted());
 reg [23:0] addr=0;
 reg wr_n=1,rd_n=1;
 reg [7:0] din=0;
 wire oe,dir,hf,nf;
 wire [7:0] dout;
 wire request;
 wire [21:0] rom_addr;
 reg response=0;
 reg [21:0] reply_addr=0;
 always @(posedge nes)begin response<=request;if(request)reply_addr<=rom_addr;end
 nes_direct206 dut(.nes_clk(nes),.host_clk(host),.reset(reset),.transport_fault(input_error||sink_error),
`ifdef WITNESS642
  .input_error(input_error),.sink_error(sink_error),
`endif
  .lease_valid(lease),.lease_fault(lease_fault),.retire_permitted(permitted),.captured_generation(captured_gen),
  .captured_epoch(epoch),.live_epoch(32'd1),.source_ready(1'b1),.source_is_rom(1'b1),.source_writing(1'b0),
  .reader_drained(drained),.retire_commit(retire),.retire_generation(retired_gen),.core_fault(core_error_in),
  .qualified_slot(1'b1),.core_safe(1'b1),.core_request(1'b0),.core_address(22'd0),
  .cap_start(1'b0),.cap_seal(1'b0),.cap_sample(1'b0),.cap_generation(16'd0),.cap_address(17'd0),.cap_data(8'd0),
  .mem_ready(1'b1),.mem_response(response),.mem_error(1'b0),.mem_response_address(reply_addr),.mem_data(8'd0),
  .mem_request(request),.mem_address(rom_addr),.core_ready(),.core_response(),.core_error(),
  .core_response_address(),.core_data(),.plan_closed(),
  .SPI_SS(ss197),.SPI_SCK(sck197),.SPI_MOSI(mosi197),.spi_selected(selected197),.spi_miso(miso197),
  .address(addr),.read_n(rd_n),.write_n(wr_n),.data_in(din),.data_out(dout),.oe_n(oe),.dir(dir),
  .host_fault(hf),.nes_fault(nf));
 integer scenario=-1, first=0;
 task origin(input integer code);
  if(scenario>=0 && first==0) begin
   first=code;
   $display("FIRST case=%0d t_ps=%0.0f circuit=%0d accepted=%0d",scenario,$realtime*1000,code,dut.endpoint.accepted);
  end
 endtask
 always @(posedge dut.transport.hf) origin(1);
 always @(posedge dut.transport.nf) origin(2);
 always @(posedge dut.command_error) origin(3);
 always @(posedge dut.spi_fault) origin(4);
 always @(posedge dut.bulk_fault or posedge dut.consume_error or posedge lease_fault or posedge dut.tile_fault) origin(5);
 always @(posedge dut.hc) if(scenario>=0 && !reset)
  $display("CANCEL case=%0d t_ps=%0.0f",scenario,$realtime*1000);
 task write_bus(input [23:0] a,input [7:0] b);
  @(negedge host);addr=a;din=b;wr_n=0;repeat(8)@(negedge host);wr_n=1;repeat(8)@(negedge host);
 endtask
 task batch(input [7:0] op,input [7:0] g,input bit corrupt);
  reg [7:0] tx[0:17],v,c8;
  reg [15:0] c16;
  integer n;
  n=(op=='h82)?10:3;
  tx[0]='he9;tx[1]=n;tx[2]=0;tx[3]=(n==10)?2:1;tx[4]=op;tx[5]=g;tx[6]=0;
  if(n==10)begin // Compact BG at slot 1, tag 4 after blank slot 0.
   tx[7]='h80;tx[8]=g;tx[9]=0;tx[10]=1;tx[11]=0;tx[12]=4;tx[13]=0;
  end
  c16='hffff;
  for(int i=4;i<n+4;i++) begin
   c16=c16^{tx[i],8'd0};
   repeat(8)c16=c16[15]?(c16<<1)^16'h1021:c16<<1;
  end
  if(corrupt)c16=c16^1;
  tx[n+4]=c16[15:8];tx[n+5]=c16[7:0];c8=0;
  for(int i=0;i<n+6;i++)c8=crc8_197(c8,tx[i]);
  tx[n+6]=c8;tx[n+7]='ha5;
  begin197();for(int i=0;i<n+8;i++)byte197(tx[i],v);end197();
 endtask
 task run_case(input integer which);
  reg [159:0] reply;
  reg [7:0] v;
  repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
  gen=31;capture_begin=1;@(negedge nes);capture_begin=0;gen=32;owned=1;
  @(negedge nes);release_frame=1;@(negedge nes);release_frame=0;owned=0;
  if(lease!==1 || captured_gen!==32)$fatal(1,"lease");
  first=0;scenario=which;
  batch('h82,32,0);
  status197();if(rx197[3]!==1 || rx197[5]!==1)$fatal(1,"credit before END");
  fork
   batch('h83,which==2 ? 31 : 32,which==1);
   if(which==3)begin wait(dut.endpoint.accepted==2);write_bus('h6050,'ha5);end
   if(which==4)begin wait(dut.endpoint.accepted==2);halt_nes=1;core_error_in=1;end
   if(which==5)begin wait(dut.endpoint.accepted==2);input_error=1;sink_error=1;end
   if(which==6)begin wait(dut.endpoint.accepted==2);halt_nes=1;end
  join
  fork
   status197();
   if(which==6)begin
    wait(dut.endpoint.bits==7 && !ss197);@(posedge sck197);@(posedge host);#1;core_error_in=1;
   end
  join
  for(int i=0;i<20;i++)reply[159-8*i-:8]=rx197[i];
  $display("E8 case=%0d reply=%040h",which,reply);
  if(which==0) begin
   if(first!=0 || rx197[3]!==2 || rx197[5]!==2 || rx197[6]!==1 ||
      rx197[8]!==32 || rx197[12]!==32 || rx197[14]!==1)$fatal(1,"healthy END");
   for(int i=0;i<32;i++)begin
    @(negedge host);addr='h400800+i;rd_n=0;repeat(8)@(negedge host);
    if(oe!==0||dir!==1||dout!==0)$fatal(1,"blank tile");rd_n=1;repeat(8)@(negedge host);
   end
   for(int i=0;i<4;i++)write_bus('h604c+i,rx197[14+i]);
   write_bus('h6050,'ha5);status197();
   if(rx197[3]!==2 || rx197[6]!==0 || first!=0)$fatal(1,"consume");
   // EA stands for ARM's post-display request. No PPU or ordinary ACK fixture here.
   begin : send_ea
    reg [7:0] tx[0:6],c;
    tx[0]='hea;tx[1]=32;tx[2]=0;tx[3]=0;tx[4]=2;c=0;
    for(int i=0;i<5;i++)c=crc8_197(c,tx[i]);
    tx[5]=c;tx[6]='ha5;begin197();foreach(tx[i])byte197(tx[i],v);end197();
   end
   status197();if(lease!==0 || first!=0 || rx197[3]!==1 || rx197[5]!==0)$fatal(1,"retire");
`ifdef WITNESS642
  end else begin : check_origin
   reg [7:0] host_mask,nes_mask;
   host_mask=(which==1)?8:(which==3)?64:(which==5)?3:0;
   nes_mask=(which==2)?1:(which==4||which==6)?128:0;
   if(rx197[14]!==host_mask || rx197[15]!==nes_mask || rx197[3]!==8'h80 ||
      rx197[5]!==2 || rx197[6]!==0 || hf!==1 || retire!==0 ||
      (which<=3 && first!=which))$fatal(1,"wrong first cause case %0d",which);
   // A later external fault and a cancellation echo must not overwrite the evidence.
   sink_error=1;status197();
   if(rx197[14]!==host_mask || rx197[15]!==nes_mask)$fatal(1,"overwritten origin");
  end
`else
  end else if(first!=which || reply!==160'h00d7048000020000000000000000000000000057 ||
              hf!==1 || !lease || retire)$fatal(1,"fault signature or ownership");
`endif
  halt_nes=0;core_error_in=0;input_error=0;sink_error=0;
  scenario=-1;reset=1;addr='h6040;rd_n=0;repeat(8)@(negedge nes);
  if(lease!==0 || oe!==1 || dir!==0 || dut.chunk_ready!==0 || retire!==0)$fatal(1,"STOP exposes ownership");
  rd_n=1;
 endtask
 initial begin
  run_case(0);run_case(1);run_case(2);run_case(3);run_case(0);
`ifdef WITNESS642
  run_case(4);run_case(5);run_case(6);run_case(0);
  $display("PASS642 FINISH first-cause, stopped NES, simultaneous host faults, STOP and rearm");
`endif
  $display("PASS641 three first faults same E8; normal consume/EA before and after STOP");$finish;
 end
 initial begin #5000000;$fatal(1,"641 watchdog");end
endmodule
