// Execute each user's reset vector on the same T65, PPU and cartridge as the
// fitted image. External memories here have ideal access times.
`timescale 1ns/1ps
module cart_boot1056_tb #(parameter MAPPER=3);
 reg clk=0, reset=1;
 always #5 clk=!clk;
 wire [24:0] ca;
 wire [21:0] pa;
 wire cw,pw;
 wire [7:0] cd,pd;
 reg [7:0] prg[0:1048575], chr[0:262143];
 bit [7:0] ram[0:2047], work_ram[0:8191], nt[0:2047];
 wire [7:0] cq=ca[24:11]==14'h700 ? ram[ca[10:0]] :
               ca[24:13]==12'h1e0 ? work_ram[ca[12:0]] : prg[ca[19:0]];
 wire [7:0] pq=pa[21:11]==11'h740 ? nt[pa[10:0]] : chr[pa[17:0]];
 nes_probe dut(.clk(clk),.reset_nes(reset),.cold_reset(reset),
  .cpumem_addr(ca),.cpumem_write(cw),.cpumem_dout(cd),.cpumem_din(cq),
  .ppumem_addr(pa),.ppumem_write(pw),.ppumem_dout(pd),.ppumem_din(pq),
  .native_oam_address(8'd0),.chr_32k(1'b0),.joypad1_data(5'd0),.joypad2_data(5'd0)
`ifdef CART_RAM
  ,.request_pause(1'b0),.request_save(1'b0),.request_load(1'b0),.stream_done(1'b0),
   .stream_read(64'd0),.state_rdata(8'd0)
`endif
 );
 integer n,fd,ticks,reads,vector_stage,ppu_writes,ram_writes;
 reg [15:0] reset_vector;
 always @(posedge clk) begin
  if(cw && ca[24:11]==14'h700) begin ram[ca[10:0]]<=cd;ram_writes++;end
  if(cw && ca[24:13]==12'h1e0)work_ram[ca[12:0]]<=cd;
  if(pw && pa[21:11]==11'h740)nt[pa[10:0]]<=pd;
  if(pw && (MAPPER==5 || MAPPER==7) && pa[21:13]==9'h100)chr[pa[12:0]]<=pd;
  if(!reset && dut.core.cpu_ce)begin
   if(dut.core.cpu_rnw && dut.core.cpu_addr[15])begin
    if($isunknown(dut.core.internal_data_bus))$fatal(1,"unknown CPU ROM read at %h",dut.core.cpu_addr);
    reads++;
    case(vector_stage)
     0:if(dut.core.cpu_addr==16'hfffc)begin reset_vector[7:0]=dut.core.internal_data_bus;vector_stage++;end
     1:if(dut.core.cpu_addr==16'hfffd)begin reset_vector[15:8]=dut.core.internal_data_bus;vector_stage++;end
     2:if(dut.core.cpu_addr==reset_vector)vector_stage++;
    endcase
   end
   if(!dut.core.cpu_rnw && dut.core.cpu_addr[15:13]==1)ppu_writes++;
   if(vector_stage==3 && reads>=1500 && ppu_writes>=3 && ram_writes>=4)begin
    $display("PASS CPU mapper=%0d vector=%04h reads=%0d ppu_writes=%0d ram_writes=%0d",MAPPER,reset_vector,reads,ppu_writes,ram_writes);
    $finish;
   end
  end
 end
 initial begin
  reads=0;vector_stage=0;ppu_writes=0;ram_writes=0;
  fd=$fopen("prg.bin","rb");n=$fread(prg,fd);$fclose(fd);if(n<32768)$fatal;
  if(MAPPER==3 || MAPPER==21)begin fd=$fopen("chr.bin","rb");n=$fread(chr,fd);$fclose(fd);if(n<32768)$fatal;end
  else for(n=0;n<8192;n++)chr[n]=0;
  repeat(80)@(negedge clk);
  reset=0;
  repeat(3000000)@(negedge clk);
  $fatal(1,"boot timeout vector=%h stage=%d pc=%h reads=%d ppu writes=%d ram writes=%d",reset_vector,vector_stage,dut.core.cpu_addr,reads,ppu_writes,ram_writes);
 end
endmodule
