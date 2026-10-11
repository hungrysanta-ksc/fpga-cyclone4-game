// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module apu162_tb;
 reg clk=0,reset=1,cold=1;always #5 clk=~clk;
 integer div=0;reg parity=0;
 always @(posedge clk)if(reset)begin div<=0;parity<=0;end else if(div==11)begin div<=0;parity<=!parity;end else div<=div+1;
 wire ce=div==11,phi2=div>4;
 reg [15:0] addr=0;wire [15:0] cpu_addr=addr;reg cpu_rnw=1;reg [7:0] data=0;
 wire apu_cs=cpu_addr[15:5]==11'b0100_0000_000;
 wire candidate_cs=GATE_FROM_ACTUAL_NES;
 wire ack,req,get_ce,put_ce,reading,enable,pause_cpu;wire [15:0] sample_address,dma_address,sample;
 APU #(.SSREG_INDEX_TOP(0),.SSREG_INDEX_DMC1(1),.SSREG_INDEX_DMC2(2),.SSREG_INDEX_FCT(3)) apu(
 .MMC5(1'b0),.clk(clk),.PHI2(phi2),.ce(ce),.reset(reset),.cold_reset(cold),.allow_us(1'b0),.PAL(1'b0),
 .ADDR(addr[4:0]),.DIN(data),.RW(cpu_rnw),.CS(candidate_cs),.audio_channels(5'b11111),.DmaData(8'h55),
 .get_or_put(parity),.DmaAck(ack),.DOUT(),.Sample(sample),.DmaReq(req),.DmaAddr(sample_address),.IRQ(),.get_ce(get_ce),.put_ce(put_ce),
 .SaveStateBus_Din(64'd0),.SaveStateBus_Adr(10'd0),.SaveStateBus_wren(1'b0),.SaveStateBus_rst(cold),.SaveStateBus_load(1'b0),.SaveStateBus_Dout());
 DmaController dma(.clk(clk),.ce(ce),.reset(reset),.put_cycle(parity),.put_ce(put_ce),.get_ce(get_ce),
 .sprite_trigger(apu_cs && addr[4:0]==5'h14 && !cpu_rnw),.dmc_trigger(req),.cpu_read(cpu_rnw),
 .data_from_cpu(data),.dma_data_to_ram(8'h55),.dmc_dma_addr(sample_address),.aout(dma_address),.aout_enable(enable),
 .read(reading),.data_to_ram(),.dmc_ack(ack),.pause_cpu(pause_cpu));
 integer reads=0,writes=0,dmc_reads=0,changes=0;reg [15:0] old_sample=0;reg dmc_phase=0;
 always @(posedge clk)if(!reset)begin
  if(^sample===1'bx)$fatal(1,"unknown audio sample");
  if(sample!=old_sample)changes=changes+1;old_sample=sample;
  if(ce&&enable)begin
   if(dmc_phase)begin
    if(reading)begin
     if(dma_address!==16'hc000+dmc_reads)$fatal(1,"DMC address %h",dma_address);
     dmc_reads=dmc_reads+1;
    end
   end else if(reading)begin
    if(dma_address!==16'h0200+reads)$fatal(1,"OAM address");reads=reads+1;
   end else begin if(dma_address!==16'h2004)$fatal(1,"OAM dest");writes=writes+1;end
  end
 end
 task wr(input [15:0] a,input [7:0] d);begin
  @(negedge clk);addr=a;data=d;cpu_rnw=0;repeat(12)@(negedge clk);cpu_rnw=1;addr=0;repeat(48)@(negedge clk);
 end endtask
 integer i;
 initial begin
  repeat(30)@(negedge clk);cold=0;reset=0;repeat(30)@(negedge clk);
  for(i=0;i<32;i=i+1)begin addr=16'h4000+i;cpu_rnw=0;#1;if(!candidate_cs)$fatal(1,"write blocked");cpu_rnw=1;#1;if(!candidate_cs)$fatal(1,"read blocked");end
  addr=0;
  wr(16'h4017,8'h40);wr(16'h4015,8'h0f);wr(16'h4000,8'hbf);wr(16'h4001,8'h00);wr(16'h4002,8'h2a);wr(16'h4003,8'h08);
  if(apu.enabled_buffer!==15)$fatal(1,"APU channel enable");
  wr(16'h4014,8'h02);wait(!pause_cpu);repeat(40)@(negedge clk);
  if(reads!=256||writes!=256||changes<2)$fatal(1,"OAM/audio counts %d %d %d",reads,writes,changes);
  dmc_phase=1;
  wr(16'h4010,8'h0f);wr(16'h4012,0);wr(16'h4013,1);wr(16'h4015,8'h1f);
  repeat(110000)@(negedge clk);
  if(dmc_reads!=17)$fatal(1,"DMC completion %d",dmc_reads);
  wr(16'h4015,0);repeat(100)@(negedge clk);if(req)$fatal(1,"DMC disable");
  $display("PASS162 APU all32 read/write OAM256+256 DMC17 pulsechanges=%d",changes);$finish;
 end
 initial begin #2000000;$fatal(1,"APU watchdog");end
endmodule
