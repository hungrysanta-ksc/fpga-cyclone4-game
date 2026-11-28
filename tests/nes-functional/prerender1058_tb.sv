`timescale 1ns/1ps
// Pre-render mask restart sensitivity test. The STOP file gives the sample
// state, not the preceding CPU trace. Vary the phase of a competing PRG read.
module prerender1058_tb;
 reg clk=0, reset=1, ce=0;
 always #5 clk=!clk;
 reg [8:0] dot=0;
 reg [2:0] enables=0;
 wire [13:0] pins,hint;
 wire raw_hint,early,read_ppu,ale;
 wire [1:0] ntsc=0;
 PPU p(.clk(clk),.ce(ce),.reset(reset),.cold_reset(reset),.sys_type(ntsc),
       .read(1'b0),.write(1'b0),.vram_addr(pins),.vram_r(read_ppu),
       .game147_prefetch_hint(raw_hint),.game160_restart_hint(early),
       .game148_hint_logic(hint),.rom_ppu_address_valid(ale),.vram_dbus_in(8'hb8),
       .SaveStateBus_load(1'b0),.SaveStateBus_wren(1'b0));
 reg mapper_write=0;
 reg [15:0] cpu=0;
 reg [7:0] din=0;
 wire [17:0] chr,pred;
 nes_cart1056 #(.MAPPER(21)) cart(.clk(clk),.reset(reset),.ce(1'b1),
    .write_cpu(mapper_write),.preview_write(1'b0),.cpu(cpu),.data(din),
    .ppu(pins),.lookahead(hint),.chr(chr),.predicted_chr(pred));
 wire [21:0] addr=pins[13]?22'h3a0000:{4'h8,chr};
 reg cpu_read=0, cpu_check=0;
 reg [24:0] cpu_addr=0;
 wire req,valid,cvalid,fail;
 wire [63:0] ctx;
 wire [21:0] requested;
 reg [21:0] tag=0;
 reg [2:0] latency=0;
 wire reply=latency==1;
 reg [7:0] rom_byte;
 wire [7:0] result;
 nes_rom_early service(.clk(clk),.reset(reset),.ppu_prefetch_valid(raw_hint && (early || valid || pins[13])),
   .ppu_prefetch_address({4'h8,pred}),.cpu_address_valid(cpu_read),.cpumem_read(cpu_read),
   .cpu_sample(cpu_check),.cpumem_addr(cpu_addr),.cpu_valid(cvalid),
   .ppu_address_valid(ale),.ppumem_addr(addr),.ppumem_read(read_ppu),.ppu_sample(ce && read_ppu),
   .ppu_valid(valid),.ppu_data(result),.rom_ready(latency==0),.rom_request(req),
   .rom_address(requested),.rom_response(reply),.rom_response_address(tag),.rom_error(1'b0),
   .rom_data(rom_byte),.chr_plane1(8'h38),.fault_trigger(fail),.fault_context(ctx));
 always @(posedge clk)begin
  if(reset)latency<=0;
  else if(req)begin tag<=requested;latency<=5;end
  else if(latency!=0)latency<=latency-1'b1;
 end
 integer phase,k,issue,old;
 initial begin
  old=$test$plusargs("OLD");
  force p.scanline=511;force p.cycle=dot;force p.is_pre_render_line=1;force p.re_sr=enables;
  force p.read_2007_delayed=0;force p.write_2007_delayed=0;
  force p.vram=15'h2000;force p.bg_name_table=8'h12;
  force p.bg_patt=1;force p.bg_patt1=1;force p.sprite_load_en=0;
  for(phase=0;phase<4;phase++)begin
   @(negedge clk);reset=1;cpu_read=0;cpu_check=0;ce=0;dot=0;enables=0;
   repeat(2)@(negedge clk);reset=0;mapper_write=1;cpu=16'hd000;din=12;
   @(negedge clk);cpu=16'hd002;din=3;
   @(negedge clk);mapper_write=0;p.vram_a_byte=8'h22;issue=-1;
   for(k=0;k<28;k++)begin
    @(negedge clk);dot=k/4;ce=k%4==3;
    enables=dot<4?0:dot==4?1:dot==5?3:7;
    cpu_read=k>=8+phase;cpu_addr=25'h1b21;cpu_check=k==27;
    rom_byte=tag[21]?8'h91:8'ha4;
    @(posedge clk);
    if(req && requested==22'h20f122)issue=k;
    if(k==27)begin
     if(addr!==22'h20f122 || !ce || !read_ppu || !cvalid)$fatal(1,"sample inputs");
     if(old && (!fail || ctx[46:25]!=22'h20f122 || ctx[54:47]!=2))
       $fatal(1,"old fault context %h issue %0d",ctx,issue);
     if(!old && (fail || !valid || result!==8'h91 || issue>=24))$fatal(1,"late or wrong byte");
     $display("SAMPLE phase=%0d old=%0d request=%0d sample=%0d context=%h",phase,old,issue,k,ctx);
    end
   end
  end
  @(negedge clk);reset=1;#1;if(req || valid)$fatal(1,"STOP");
  $display("PASS_PRERENDER1058");$finish;
 end
endmodule
