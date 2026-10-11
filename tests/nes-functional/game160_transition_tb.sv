// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module transition160_tb;
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
wire rom_cpu_address_valid,rom_ppu_address_valid,rom_cpu_sample,game147_prefetch_hint,game160_restart_hint;
 wire [63:0] ppu_fault_state154;
 nes_probe dut(.*);
 wire [7:0] external_cpu_data,external_ppu_data;
 wire rom_cpu_valid,rom_ppu_valid,rom_fault;
 wire [3:0] rom_error_code;wire [63:0] fault_context;wire fault_trigger;
 wire rom_ready,rom_request,rom_response,rom_error;
 wire [21:0] rom_address,rom_response_address;wire [7:0] rom_data;
 nes_rom_early rom_service(
 .ppu_prefetch_valid(game147_prefetch_hint && (game160_restart_hint || rom_ppu_valid || (ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800))),.ppu_prefetch_address(game148_hint_physical),
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

 reg [8:0] dot160=329;reg ce160=0,ppu_write160=0;
 reg [23:0] cpuaddr160=0;reg [7:0] cpudata160=0;reg rnw160=1;reg [4:0] div160=12;
 integer step160,checked160=0,failed160=0,target160=336,latch160=0;
 task wr160(input [15:0] a,input [7:0] d);
  @(negedge clk);cpuaddr160=a;cpudata160=d;rnw160=0;div160=10;
  @(negedge clk);cpuaddr160=0;rnw160=1;div160=12;
 endtask
 initial begin
  unused155=$value$plusargs("CONTROL=%d",control155);
  unused155=$value$plusargs("DOT=%d",target160);
  unused155=$value$plusargs("LATCH=%d",latch160);
  if(target160!=334 && target160!=336)$fatal(1,"unsupported test dot");
  if(control155)force dut.core.ppu.restart160=0;
  $readmemh("prg.hex",prg);$readmemh("chr.hex",chr);
  force dut.core.ppu.cycle=dot160;force dut.core.ppu.scanline=9'd193;
  force dut.core.ppu.bg_patt=0;force dut.core.ppu.bg_patt1=0;
  force dut.core.ppu.bg_name_table=8'h07;force dut.core.ppu.vram=15'h0b00;
  force dut.core.ppu.ce=ce160;force dut.core.ppu.read=0;
  force dut.core.ppu.write=ppu_write160;force dut.core.ppu.ppu_ain=3'd1;
  force dut.core.ppu.ppu_dbus=8'h08;
  force tap_ce=ce160;
  force dut.core.cpu_addr_full=cpuaddr160;force dut.core.cpu_rnw=rnw160;force dut.core.cpu_dout=cpudata160;
  force dut.core.dma_aout_enable=0;force dut.core.div_cpu=div160;
  repeat(8)@(negedge clk);reset_request=0;wait(!reset);wait(!dut.core.reset_noSS);wait(rom_ready);
  // Clock the real PPUDATA pipelines to known idle values before the case.
  repeat(8)begin @(negedge clk);ce160=1;@(negedge clk);ce160=0;end
  wr160(16'h8000,0);wr160(16'h8001,8'h5c);wr160(16'h8000,1);wr160(16'h8001,8'h5e);
  // Existing address-latch state and name byte from earlier history are seeded.
  // Actual2001 register write and re_sr shift, ALE and latch behavior are live.
  dut.core.ppu.vram_a_byte=latch160;
  for(step160=0;step160<60;step160++)begin
   @(negedge clk);dot160=target160-7+step160/4;ce160=step160%4==3;
   ppu_write160=dot160==target160-4;
   cpuaddr160=step160>=20?24'hf86e:0;div160=step160>=20?((step160-20)%12)+1:12;
   @(posedge clk);
   if($isunknown({rom_request,rom_response,rom_ready,rom_ppu_valid,tap_ce,ppumem_read,fault_trigger,ppumem_addr,game147_prefetch_hint,rom_service.ppu_prefetch_valid}))$fatal(1,"unknown transition evidence");
   $display("TRACE160 step=%0d dot=%0d re=%b render=%b rawhint=%b hint=%b/%h ppu=%h ale=%b latch=%h req=%b/%h resp=%b ready=%b valid=%b sample=%b fault=%b",step160,dot160,dut.core.ppu.re_sr,dut.core.ppu.is_rendering_d,game147_prefetch_hint,rom_service.ppu_prefetch_valid,game148_hint_physical,ppumem_addr,dut.core.ppu.ALE,dut.core.ppu.vram_a_byte,rom_request,rom_address,rom_response,rom_ready,rom_ppu_valid,tap_ce&&ppumem_read,fault_trigger);
   if(fault_trigger)failed160=1;
   if(step160==31 && (ppumem_addr!==(22'h217000 | latch160) || !tap_ce || !ppumem_read))$fatal(1,"transition boundary mismatch");
   if(!failed160 && tap_ce && ppumem_read && ppumem_addr>=22'h200000 && ppumem_addr<22'h220000)begin
    if(!rom_ppu_valid || ppumem_din!==chr[ppumem_addr[16:0]])$fatal(1,"wrongPPU160");checked160++;
   end
  end
  if(control155 && (!failed160 || rom_error_code!=2))$fatal(1,"old boundary must fail");
  if(!control155 && (failed160 || rom_error_code!=0 || checked160<1))$fatal(1,"restart preview must supply correct data");
  $display("CASE160 failed=%0d error=%0d checked=%0d",failed160,rom_error_code,checked160);$display("DONE160");$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog160");end
endmodule
