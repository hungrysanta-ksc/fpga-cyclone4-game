// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module eligibility159_tb;
 reg clk=0,mem_clk=0,reset_request=1;
 always #23.280423 clk=~clk;
 real phase155;integer unused155,control155;
 initial begin unused155=$value$plusargs("PHASE=%f",phase155);#(phase155);forever #2.9761905 mem_clk=~mem_clk;end
 wire init_reset,reset,memory_ready;
 wire common_reset=reset_request || !memory_ready;
 nes_domain_reset124 init_release(clk,reset_request,init_reset);
 nes_domain_reset124 core_release(clk,common_reset,reset);
 wire reset_nes=reset,cold_reset=reset,chr_32k=0;
 wire [7:0] cpumem_din,ppumem_din,cpumem_dout,ppumem_dout;
 wire [24:0] cpumem_addr;wire [21:0] ppumem_addr;
 wire cpumem_read,cpumem_write,ppumem_read,ppumem_write;
 wire [5:0] color;wire [2:0] emphasis;wire [8:0] cycle,scanline;wire [15:0] sample;
 wire [1:0] joypad_clock;wire [2:0] joypad_out;wire apu_ce,hsync,hblank,vsync,vblank;
 wire [4:0] joypad1_data=0,joypad2_data=0;
 wire tap_ce,tap_bgp,tap_mode,tap_ppu_change,tap_mapper_change;
 wire [2:0] tap_fine;wire [14:0] tap_scroll;wire [95:0] tap_palette;wire [1:0] tap_attribute;
 wire [21:0] game148_hint_physical;
wire rom_cpu_address_valid,rom_ppu_address_valid,rom_cpu_sample,game147_prefetch_hint;
 wire [63:0] ppu_fault_state154;
 nes_probe dut(.*);
 wire [7:0] external_cpu_data,external_ppu_data;
 wire rom_cpu_valid,rom_ppu_valid,rom_fault;
 wire [3:0] rom_error_code;wire [63:0] fault_context;wire fault_trigger;
 wire rom_ready,rom_request,rom_response,rom_error;
 wire [21:0] rom_address,rom_response_address;wire [7:0] rom_data;
 nes_rom_early rom_service(
 .ppu_prefetch_valid(game147_prefetch_hint && (rom_ppu_valid || (ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800))),.ppu_prefetch_address(game148_hint_physical),
 .clk(clk),.reset(reset),.cpu_address_valid(rom_cpu_address_valid),.ppu_address_valid(rom_ppu_address_valid),
 .cpumem_addr(cpumem_addr),.cpumem_read(cpumem_read),.cpu_sample(rom_cpu_sample),
 .ppumem_addr(ppumem_addr),.ppumem_read(ppumem_read),.ppu_sample(tap_ce && ppumem_read),
 .cpu_data(external_cpu_data),.ppu_data(external_ppu_data),.cpu_valid(rom_cpu_valid),.ppu_valid(rom_ppu_valid),
 .rom_ready(rom_ready),.rom_request(rom_request),.rom_address(rom_address),
 .rom_response(rom_response),.rom_error(rom_error),.rom_response_address(rom_response_address),.rom_data(rom_data),
 .fault_trigger(fault_trigger),.fault_context(fault_context),.fault(rom_fault),.error_code(rom_error_code));
 nes_local_memory local_memory(.clk(clk),.reset(init_reset),
 .cpumem_addr(cpumem_addr),.cpumem_write(cpumem_write),.cpumem_dout(cpumem_dout),
 .ppumem_addr(ppumem_addr),.ppumem_write(ppumem_write),.ppumem_dout(ppumem_dout),
 .external_cpu_data(external_cpu_data),.external_ppu_data(external_ppu_data),
 .cpumem_din(cpumem_din),.ppumem_din(ppumem_din),.init_done(memory_ready));
 wire [21:0] psram_address;wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;wire [15:0] psram_data;
 nes_rom_physical #(.READ_CYCLES(16)) physical(.clk(clk),.mem_clk(mem_clk),.reset(common_reset),
 .check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),.check_ready(),.check_response(),.check_response_address(),.check_data(),
 .rom_request(rom_request),.rom_address(rom_address),.rom_ready(rom_ready),.rom_response(rom_response),
 .rom_error(rom_error),.rom_response_address(rom_response_address),.rom_data(rom_data),
 .psram_address(psram_address),.psram_1ce(psram_1ce),.psram_2ce(psram_2ce),.psram_oe(psram_oe),
 .psram_we(psram_we),.psram_bhe(psram_bhe),.psram_ble(psram_ble),.psram_data(psram_data));
 reg [7:0] prg[0:262143],chr[0:131071];
 function automatic [7:0] value(input [23:0] address);
  if(address<24'h040000)value=prg[address[17:0]];
  else if(address>=24'h200000 && address<24'h220000)value=chr[address[16:0]];
  else value=8'hxx;
 endfunction
 wire selected=(!psram_1ce ^ !psram_2ce) && !psram_oe && psram_we;
 wire [23:0] base={psram_address,psram_1ce,1'b0};
 assign #70 psram_data=selected?{psram_bhe?8'hzz:value(base),psram_ble?8'hzz:value(base+24'd1)}:16'hzzzz;

 reg [8:0] dot159=1;reg render159=0,ce159=0;
 reg [23:0] cpuaddr159=0;reg [7:0] cpudata159=0;
 reg rnw159=1,dma159=0,dmaread159=1;reg [15:0] dmaaddr159=0;
 reg [4:0] div159=12;
 integer offset159,step159,start159,failed159,requests159,checked159,write_reads159,elig159=0;
 integer source159,direction159,phase159,samples159,guard159;
 task wr159(input [15:0] a,input [7:0] d);
  @(negedge clk);cpuaddr159=a;cpudata159=d;rnw159=0;div159=10;
  @(negedge clk);cpuaddr159=0;rnw159=1;div159=1;
 endtask
 initial begin
  unused155=$value$plusargs("CONTROL=%d",control155);
  if(control155)force rom_cpu_address_valid=dut.core.prg_addr[15] && dut.core.prg_allow;
  $readmemh("prg.hex",prg);$readmemh("chr.hex",chr);
  force dut.core.ppu.cycle=dot159;force dut.core.ppu.scanline=9'd193;
  force dut.core.ppu.bg_patt1=0;force dut.core.ppu.is_rendering_d=render159;
  force dut.core.ppu.rendering_enabled=render159;force dut.core.ppu.bg_name_table=8'ha1;
  force dut.core.ppu.vram=15'd0;force dut.core.ppu.read_2007_delayed=0;force dut.core.ppu.write_2007_delayed=0;
  force dut.core.ppu.ce=ce159;force dut.core.ppu.read=0;force dut.core.ppu.write=0;force tap_ce=ce159;
  // Drive only CPU/DMA output buses. Keep raw mux, mapper write/allow,
  // cart_pre/cart_ce, early eligibility, cpumem_read and sample wires live.
  force dut.core.cpu_addr_full=cpuaddr159;force dut.core.cpu_rnw=rnw159;force dut.core.cpu_dout=cpudata159;
  force dut.core.dma_aout_enable=dma159;force dut.core.dma_read=dmaread159;force dut.core.dma_aout=dmaaddr159;
  force dut.core.dma_data_to_ram=cpudata159;force dut.core.div_cpu=div159;
  for(offset159=-1;offset159<12;offset159=offset159+1)begin
   @(negedge clk);reset_request=1;render159=0;ce159=0;dot159=1;cpuaddr159=0;rnw159=1;div159=12;dma159=0;
   repeat(8)@(negedge clk);reset_request=0;
   wait(!reset);wait(!dut.core.reset_noSS);wait(rom_ready);
   wr159(16'h8000,6);wr159(16'h8001,8'h1e);
   wr159(16'h8000,1);wr159(16'h8001,8'h16);
   failed159=0;requests159=0;checked159=0;write_reads159=0;render159=1;start159=offset159==-1?16:12+offset159;
   // Captured-prefix case: delay initial acceptance, then seed the low-plane
   // previous cache seen in158 while its duplicate read is in flight.
   // This reconstructs an observed boundary state, not its earlier history.
   if(offset159==-1)force rom_ready=0;
   for(step159=0;step159<44;step159=step159+1)begin
    @(negedge clk);dot159=1+step159/4;ce159=(step159%4==3);
    div159=((step159-start159+36)%12)+1;
    if(offset159==-1 && step159==14)release rom_ready;
    if(offset159==-1 && step159==15)begin
     rom_service.ppu_previous_cached=1;rom_service.ppu_previous_tag=17'h05a10;rom_service.ppu_previous_byte=chr[17'h05a10];
    end
    if(step159>=start159 && step159<start159+12)begin cpuaddr159=24'h8001;cpudata159=8'h5e;rnw159=0;end
    else begin cpuaddr159=(offset159==-1 && step159>=28)?24'hc001:24'd0;rnw159=1;end
    @(posedge clk);
    if(rom_request)begin requests159++;if(rom_address<22'h40000 && !dut.core.mr_int)write_reads159++;end
    if(rom_request || rom_response || fault_trigger || (step159>=16 && step159<=31))
     $display("TRACE159 offset=%0d step=%0d dot=%0d div=%0d rawread=%b early=%b allow=%b pre=%b ppu=%h hint=%b/%h req=%b/%h resp=%b valid=%b fault=%b",offset159,step159,dot159,div159,dut.core.mr_int,rom_cpu_address_valid,dut.core.prg_allow,dut.core.cart_pre,ppumem_addr,game147_prefetch_hint,game148_hint_physical,rom_request,rom_address,rom_response,rom_ppu_valid,fault_trigger);
    if(fault_trigger)failed159=1;
    if(!failed159 && ce159 && ppumem_read && ppumem_addr>=22'h200000 && ppumem_addr<22'h220000)begin
     if(!rom_ppu_valid || ppumem_din!==chr[ppumem_addr[16:0]])$fatal(1,"wrong PPU byte");checked159++;
    end
    if(!control155 && !dut.core.mr_int && rom_cpu_address_valid)$fatal(1,"write qualifies early read");
   end
   $display("CASE159 offset=%0d control=%0d failed=%0d error=%0d checked=%0d requests=%0d write_reads=%0d",offset159,control155,failed159,rom_error_code,checked159,requests159,write_reads159);
  end
  // Combinational eligibility table includes DMA bus mux and every CPU phase.
  @(negedge clk);reset_request=1;render159=0;ce159=0;rnw159=1;cpuaddr159=0;div159=12;
  repeat(8)@(negedge clk);reset_request=0;wait(!reset);wait(!dut.core.reset_noSS);
  for(source159=0;source159<2;source159++)for(direction159=0;direction159<2;direction159++)for(phase159=1;phase159<=12;phase159++)begin
   @(negedge clk);dma159=source159;rnw159=direction159;dmaread159=direction159;
   cpuaddr159=24'hc001;dmaaddr159=16'hc001;div159=phase159;#1;
   if(dut.core.mr_int!==direction159[0])$fatal(1,"raw bus direction mismatch");
   if(!control155 && rom_cpu_address_valid!==(direction159[0] && dut.core.prg_allow))$fatal(1,"eligibility mismatch");
   if(cpumem_read!==(direction159[0] && dut.core.cart_pre && dut.core.prg_allow))$fatal(1,"read strobe changed");
   if(rom_cpu_sample!==((phase159==11 || phase159==12) && direction159[0] && dut.core.prg_allow))$fatal(1,"sample contract changed");
   elig159++;
  end
  $display("ELIGIBILITY159 %0d",elig159);
  // Actual tagged data on unchanged CPU and DMA read/sample paths.
  for(source159=0;source159<2;source159++)begin
   @(negedge clk);reset_request=1;cpuaddr159=0;dma159=0;rnw159=1;div159=12;
   repeat(8)@(negedge clk);reset_request=0;wait(!reset);wait(!dut.core.reset_noSS);wait(rom_ready);
   samples159=0;
   for(step159=0;step159<36;step159++)begin
    @(negedge clk);dma159=source159;rnw159=1;dmaread159=1;cpuaddr159=24'hc123;dmaaddr159=16'hc123;div159=(step159%12)+1;
    @(posedge clk);
    if(rom_cpu_sample)begin
     if(!rom_cpu_valid || cpumem_din!==prg[cpumem_addr[17:0]] || rom_fault)$fatal(1,"CPU/DMA data missed");samples159++;
    end
   end
   if(samples159!=6)$fatal(1,"CPU/DMA sample count");
   $display("READ159 source=%0d samples=%0d",source159,samples159);
  end
  $display("DONE159");$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog159");end
endmodule
