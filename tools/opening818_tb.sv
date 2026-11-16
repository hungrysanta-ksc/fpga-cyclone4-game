`timescale 1ns/1ps
module opening818_tb;
 reg clk=0, cold=1;
 always #23 clk=~clk;
 wire ready;
 wire reset=cold||!ready;
 wire [24:0] ca; wire [21:0] pa; wire cw,pw,cr,pr,ce;
 wire [7:0] co,po,ci,pi;
 wire [8:0] x,y; wire [5:0] color;
 reg [7:0] prg[0:262143],chr[0:131071];
 wire [7:0] rom_cpu=prg[ca[17:0]],rom_ppu=chr[pa[16:0]];
 nes_probe dut(.clk(clk),.reset_nes(reset),.cold_reset(reset),.chr_32k(1'b0),.native_oam_address(8'd0),
   .joypad1_data(5'd0),.joypad2_data(5'd0),.cpumem_addr(ca),.cpumem_dout(co),.cpumem_din(ci),
   .cpumem_read(cr),.cpumem_write(cw),.ppumem_addr(pa),.ppumem_dout(po),.ppumem_din(pi),
   .ppumem_read(pr),.ppumem_write(pw),.cycle(x),.scanline(y),.color(color),.tap_ce(ce));
 nes_local_memory mem(.clk(clk),.reset(cold),.native_nt_address(11'd0),
    .cpumem_addr(ca),.cpumem_write(cw),.cpumem_dout(co),.ppumem_addr(pa),.ppumem_write(pw),.ppumem_dout(po),
    .external_cpu_data(rom_cpu),.external_ppu_data(rom_ppu),.cpumem_din(ci),.ppumem_din(pi),.init_done(ready));
 integer frames=0,nt=0,chr_reads=0;
 reg [63:0] colors=0;
 string prefix;
 initial begin
    if(!$value$plusargs("game=%s",prefix)) $fatal;
    $readmemh({prefix,"-prg.hex"},prg);
    $readmemh({prefix,"-chr.hex"},chr);
    repeat(5) @(negedge clk);
    cold=0;
 end
 always @(posedge clk) if(!reset && mem.native_nt_write) nt<=nt+1;
 always @(posedge clk) if(!reset && ce) begin
    if(pr && pa>=22'h200000 && pa<22'h220000) chr_reads<=chr_reads+1;
    if(y<240 && x<256 && !$isunknown(color)) colors[color]<=1'b1;
    if(y==240 && x==0) begin
      frames<=frames+1;
      if(frames==0 || frames%4==3) $display("OPEN818 %s frame=%0d nt=%0d chr=%0d colors=%0d",prefix,frames+1,nt,chr_reads,$countones(colors));
      if(frames>=7 && nt>0 && chr_reads>0 && $countones(colors)>=4) begin
        $display("PASS818 %s frames=%0d nt=%0d chr=%0d colors=%0d",prefix,frames+1,nt,chr_reads,$countones(colors));
        $finish;
      end
      if(frames>=119) $fatal(1,"No opening pixels nt=%0d chr=%0d colors=%0d",nt,chr_reads,$countones(colors));
      colors<=0;
    end
 end
endmodule
