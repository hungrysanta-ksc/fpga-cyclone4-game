`timescale 1ns/1ps
// Actual 227 cart_top ports, four separate NROM build profiles. Exhaust all
// CPU/PPU addresses, including ROM writes, CPU RAM mirroring and nametables.
module cart_tb;
 reg [15:0] cpu;
 reg [13:0] ppu,hint;
 reg wr;
 wire [24:0] prg[0:3];
 wire [21:0] chr[0:3],hp[0:3];
 wire allow[0:3],ca[0:3],ce[0:3],a10[0:3],irq[0:3];
 generate for(genvar i=0;i<4;i=i+1)begin:g
  cart_top #(.NROM_PRG16((i&1)==0),.NROM_VERTICAL((i&2)!=0)) dut(
   .clk(1'b0),.ce(1'b1),.cpu_ce(1'b1),.paused(1'b0),.reset(1'b0),.vs_mode(1'b0),.flags(64'd0),
   .game158_preview_write(1'b0),.game148_hint_logic(hint),.game148_hint_physical(hp[i]),
   .prg_ain(cpu),.prg_write(wr),.prg_read(!wr),.prg_aout(prg[i]),.prg_allow(allow[i]),
   .prg_din(8'd0),.prg_dout(),.prg_from_ram(8'd0),.prg_bus_write(),.prg_conflict(),
   .has_savestate(),.prg_conflict_d0(),.has_flashsaves(),.prg_mask(21'h3fff),.chr_mask(20'h1fff),
   .chr_ex(1'b0),.chr_read(1'b1),.chr_write(1'b0),.chr_din(8'd0),.chr_ain_ex(14'd0),
   .chr_ain_orig(ppu),.chr_aout(chr[i]),.chr_dout(),.has_chr_dout(),.chr_allow(ca[i]),
   .vram_ce(ce[i]),.vram_a10(a10[i]),.irq(irq[i]),.mapper_addr(),.mapper_data_in(8'd0),
   .mapper_data_out(),.mapper_prg_write(),.mapper_ovr(),.audio_in(16'd0),.audio(),.diskside(),
   .fds_busy(1'b0),.fds_eject(1'b0),.fds_auto_eject(1'b0),.max_diskside(2'd0),.fds_fast(1'b0),
   .SaveStateBus_Din(64'd0),.SaveStateBus_Adr(10'd0),.SaveStateBus_wren(1'b0),
   .SaveStateBus_rst(1'b0),.SaveStateBus_load(1'b0),.SaveStateBus_Dout(),
   .Savestate_MAPRAMactive(1'b0),.Savestate_MAPRAMAddr(13'd0),.Savestate_MAPRAMRdEn(1'b0),
   .Savestate_MAPRAMWrEn(1'b0),.Savestate_MAPRAMWriteData(8'd0),.Savestate_MAPRAMReadData());
 end endgenerate
 integer n,i,j; reg [24:0] ep; reg [21:0] ec; reg nt,bit10,valid_cpu;
 initial begin
  ppu=0; hint=0; wr=0; cpu=0;
  for(n=0;n<65536;n=n+1)begin
   cpu=n; wr=n[0]; #1;
   for(i=0;i<4;i=i+1)begin
    valid_cpu=(n<8192)||((n>=32768)&&!wr);
    ep=n<8192 ? (25'h380000|(n&2047)) : ((i&1)==0 ? (n&16383) : (n&32767));
    if(allow[i]!==valid_cpu || (valid_cpu&&prg[i]!==ep) || irq[i]!==1'b0)
     $fatal(1,"CPU mapping profile=%0d address=%h write=%b",i,cpu,wr);
   end
  end
  // Test both write and read for the entire CPU ROM range.
  for(n=32768;n<65536;n=n+1)begin
   cpu=n;wr=1;#1;for(i=0;i<4;i=i+1)if(allow[i])$fatal(1,"ROM write accepted");
   wr=0;#1;for(i=0;i<4;i=i+1)begin
    ep=(i&1)==0 ? (n&16383) : (n&32767);
    if(!allow[i] || prg[i]!==ep)$fatal(1,"ROM read mismatch");
   end
  end
  for(n=0;n<16384;n=n+1)begin
   ppu=n; hint=n; #1; nt=(n&8192)!=0;
   for(i=0;i<4;i=i+1)begin
    bit10=(i&2)!=0 ? ((n&1024)!=0) : ((n&2048)!=0);
    ec=nt ? (22'h3a0000|(bit10<<10)|(n&1023)) : (22'h200000|(n&8191));
    if(chr[i]!==ec || ce[i]!==nt || a10[i]!==bit10 || ca[i]!==1'b0 || hp[i]!== (22'h200000|(n&8191)))
     $fatal(1,"PPU mapping profile=%0d address=%h",i,ppu);
   end
  end
  $display("NROM406 CART PASS CPU=65536 plus ROM writes PPU=16384 profiles=4"); $finish;
 end
endmodule
