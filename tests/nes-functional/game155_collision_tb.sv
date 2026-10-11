// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module focused155_tb;
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
 reg [8:0] dot155=1;
 reg render155=1;reg [4:0] rpipe155=0,wpipe155=0;
 reg ce155=0,cpuread155=0,cpusample155=0;
 reg [24:0] cpuaddr155=25'h10000;
 reg [7:0] name155=8'ha1;
 integer offset155,step155,failed155;
 reg [63:0] context155;
 initial begin
  unused155=$value$plusargs("CONTROL=%d",control155);
  if(control155)force dut.core.ppu.normal155=0;
  $readmemh("prg.hex",prg);$readmemh("chr.hex",chr);
  force dut.core.ppu.cycle=dot155;
  force dut.core.ppu.scanline=9'd193;
  force dut.core.ppu.bg_patt1=0;
  force dut.core.ppu.is_rendering_d=render155;
  force dut.core.ppu.rendering_enabled=1;
  force dut.core.ppu.bg_name_table=name155;
  force dut.core.ppu.vram=15'd0;
  force dut.core.ppu.read_2007_delayed=rpipe155;
  force dut.core.ppu.write_2007_delayed=wpipe155;
  force dut.core.ppu.ce=ce155;
  force dut.core.ppu.read=0;
  force dut.core.ppu.write=0;
  force dut.core.multi_mapper.prg_write=0;
  force tap_ce=ce155;
  force cpumem_addr=cpuaddr155;
  force cpumem_read=cpuread155;
  force rom_cpu_address_valid=cpuread155;
  force rom_cpu_sample=cpusample155;
  force cpumem_write=0;
  force dut.core.multi_mapper.mapper.chr_a12_invert=0;
  force dut.core.multi_mapper.mapper.chr_bank_1=8'h2f;
  for(offset155=0;offset155<12;offset155=offset155+1)begin
   @(negedge clk);reset_request=1;ce155=0;cpuread155=0;cpusample155=0;dot155=1;
   repeat(8)@(negedge clk);reset_request=0;
   wait(!reset);wait(!dut.core.reset_noSS);wait(rom_ready);failed155=0;context155=0;
   for(step155=0;step155<128;step155=step155+1)begin
    @(negedge clk);dot155=1+step155/4;ce155=(step155%4==3);
    name155=8'ha1+step155/32;
    cpuread155=(step155>=offset155);
    cpuaddr155=25'h10000+(step155>=offset155?(step155-offset155)/12:0);
    cpusample155=step155>=offset155 && ((step155-offset155)%12==11);
    @(posedge clk);
    if($isunknown({ppumem_addr,rom_request,rom_ready,rom_response,cpumem_addr,fault_trigger}))$fatal(1,"unknown model state");
    if(rom_request || rom_response || fault_trigger)
     $display("TRACE155 off=%0d step=%0d dot=%0d addr=%h req=%b/%h resp=%b/%h hint=%b/%h age=%0d fault=%b err=%0d",offset155,step155,dot155,ppumem_addr,rom_request,rom_address,rom_response,rom_response_address,game147_prefetch_hint,game148_hint_physical,rom_service.age,fault_trigger,rom_error_code);
    if(fault_trigger && !failed155)begin failed155=1;context155=fault_context;end
    if(!failed155 && cpusample155 && (!rom_cpu_valid || cpumem_din!==prg[cpuaddr155]))$fatal(1,"wrong CPU byte");
    if(!failed155 && ce155 && ppumem_read && ppumem_addr<22'h220000 && ppumem_addr>=22'h200000 && (!rom_ppu_valid || ppumem_din!==chr[ppumem_addr[16:0]]))$fatal(1,"wrong PPU byte");
   end
   $display("CASE155 offset=%0d failed=%0d error=%0d context=%h",offset155,failed155,rom_error_code,context155);
  end
  if(!control155)begin
   @(negedge clk);reset_request=1;ce155=0;cpuread155=0;cpusample155=0;
   for(integer d=1;d<=8;d++)begin
    dot155=d;#1;
    if(game147_prefetch_hint !== (d>=3 && d<=6))$fatal(1,"normal hint gate");
    if(d>=3 && d<=6 && dut.core.ppu.game148_hint_logic !== {1'b0,1'b0,name155,(d>=5),3'b000})$fatal(1,"normal address");
   end
   dot155=3;render155=0;#1;if(game147_prefetch_hint)$fatal(1,"disabled rendering hint");
   render155=1;wpipe155=1;#1;if(game147_prefetch_hint)$fatal(1,"write overlap hint");
   wpipe155=0;rpipe155=1;#1;if(game147_prefetch_hint)$fatal(1,"read pending hint");
   rpipe155=8;dot155=4;#1;
   if(!game147_prefetch_hint || dut.core.ppu.game148_hint_logic !== {1'b0,1'b0,name155[7:4],dut.core.ppu.vram_din})$fatal(1,"old overlap changed");
   rpipe155=0;dot155=259;#1;if(game147_prefetch_hint)$fatal(1,"sprite hint");
   dot155=339;#1;if(game147_prefetch_hint)$fatal(1,"endline hint");
   $display("PASS155 hint gates");
  end
  $display("DONE155");$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog155");end
endmodule
