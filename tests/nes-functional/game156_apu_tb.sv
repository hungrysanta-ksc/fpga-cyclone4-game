// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module apu156_tb;
 reg clk=0,reset=1,cold_reset=1;always #5 clk=~clk;
 integer div=0;reg parity=0;
 always @(posedge clk)if(reset)begin div<=0;parity<=0;end else if(div==11)begin div<=0;parity<=!parity;end else div<=div+1;
 wire ce=div==11,phi2=div>4;
 reg [15:0] addr=0;wire [15:0] cpu_addr=addr;reg cpu_rnw=1;reg [7:0] data=0;
 wire apu_cs=cpu_addr[15:5]==11'b0100_0000_000;
 wire candidate_cs=GATE_FROM_ACTUAL_NES;
 wire [1:0] get_ce,put_ce,request,pause_cpu,enable,reading;wire [15:0] dma_address[0:1];
 integer reads[0:1],writes[0:1];integer i;
 genvar k;
 generate for(k=0;k<2;k=k+1)begin: pair
  wire ack;wire [15:0] sample_address;
  APU #(.SSREG_INDEX_TOP(0),.SSREG_INDEX_DMC1(1),.SSREG_INDEX_DMC2(2),.SSREG_INDEX_FCT(3)) apu(.MMC5(1'b0),.clk(clk),.PHI2(phi2),.ce(ce),.reset(reset),.cold_reset(cold_reset),.allow_us(1'b0),.PAL(1'b0),
   .ADDR(addr[4:0]),.DIN(data),.RW(cpu_rnw),.CS(k==1?candidate_cs:apu_cs),.audio_channels(5'b11111),.DmaData(8'h55),
   .get_or_put(parity),.DmaAck(ack),.DOUT(),.Sample(),.DmaReq(request[k]),.DmaAddr(sample_address),.IRQ(),.get_ce(get_ce[k]),.put_ce(put_ce[k]),
   .SaveStateBus_Din(64'd0),.SaveStateBus_Adr(10'd0),.SaveStateBus_wren(1'b0),.SaveStateBus_rst(cold_reset),.SaveStateBus_load(1'b0),.SaveStateBus_Dout());
  DmaController dma(.clk(clk),.ce(ce),.reset(reset),.put_cycle(parity),.put_ce(put_ce[k]),.get_ce(get_ce[k]),
   .sprite_trigger(apu_cs && addr[4:0]==5'h14 && !cpu_rnw),.dmc_trigger(request[k]),.cpu_read(cpu_rnw),
   .data_from_cpu(data),.dma_data_to_ram(8'h55),.dmc_dma_addr(sample_address),.aout(dma_address[k]),.aout_enable(enable[k]),
   .read(reading[k]),.data_to_ram(),.dmc_ack(ack),.pause_cpu(pause_cpu[k]));
  always @(posedge clk)if(!reset && ce && enable[k])begin
   if(reading[k])begin
    if(dma_address[k]!==16'h0200+reads[k])$fatal(1,"OAM read address");reads[k]=reads[k]+1;
   end else begin if(dma_address[k]!==16'h2004)$fatal(1,"OAM dest");writes[k]=writes[k]+1;end
  end
 end endgenerate
 reg check_oam=1;reg seen_dmc=0;
 always @(posedge clk)if(!reset)begin
  if(get_ce[0]!==get_ce[1]||put_ce[0]!==put_ce[1])$fatal(1,"DMA clock changed");
  if(request[1])$fatal(1,"isolated DMC requested");
  if(request[0])seen_dmc=1;
  if(check_oam && (pause_cpu[0]!==pause_cpu[1]||enable[0]!==enable[1]))$fatal(1,"OAM changed");
 end
 task wr(input [15:0] a,input [7:0] d);begin
  @(negedge clk);addr=a;data=d;cpu_rnw=0;repeat(12)@(negedge clk);cpu_rnw=1;addr=0;
  repeat(48)@(negedge clk);
 end endtask
 initial begin
  reads[0]=0;reads[1]=0;writes[0]=0;writes[1]=0;
  repeat(30)@(negedge clk);cold_reset=0;reset=0;repeat(30)@(negedge clk);
  for(i=0;i<32;i=i+1)begin addr=16'h4000+i;cpu_rnw=0;#1;
   if(candidate_cs!==(i==23))$fatal(1,"gate write %d",i);
   cpu_rnw=1;#1;if(!candidate_cs)$fatal(1,"gate read");end
  addr=0;
  wr(16'h4017,8'h40);wr(16'h4015,8'h0f);wr(16'h4002,8'h2a);wr(16'h4003,8'h08);wr(16'h4001,8'h7f);wr(16'h4000,8'h97);
  if(pair[0].apu.enabled_buffer!==15||pair[1].apu.enabled_buffer!==0)$fatal(1,"channel enable gate");
  wr(16'h4014,8'h02);wait(!pause_cpu[0]&&!pause_cpu[1]);repeat(30)@(negedge clk);
  if(reads[0]!=256||reads[1]!=256||writes[0]!=256||writes[1]!=256)$fatal(1,"OAM counts %d %d %d %d",reads[0],reads[1],writes[0],writes[1]);
  check_oam=0;
  // Keep the DMC request pending to observe it without counting it as OAM.
  force pair[0].dma.dmc_state=0;
  wr(16'h4010,8'h0f);wr(16'h4012,8'h00);wr(16'h4013,8'h01);wr(16'h4015,8'h1f);
  repeat(20000)@(negedge clk);
  if(!seen_dmc)$fatal(1,"negative control never requested DMC");
  $display("PASS156 actual APU gate32 reads/writes,Select pulse writes,4017 retained,OAM256+256,baseline DMC active/candidate inactive,get-put identical");$finish;
 end
 initial begin #10000000;$fatal(1,"watchdog");end
endmodule
