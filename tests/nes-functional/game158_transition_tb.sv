// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module transition158_tb;
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

 reg [8:0] dot158=1;reg render158=0,ce158=0,write158=0,pre158=0,commit158=0;
 reg [15:0] address158=0;reg [7:0] data158=0;reg bg158=0;
 reg cpuread158=0;reg [24:0] cpuaddr158=25'h3c001;
 integer mode158,offset158,step158,failed158,requests158,checked158;
 task wr158(input [15:0] a,input [7:0] d);
  @(negedge clk);address158=a;data158=d;write158=1;pre158=1;commit158=1;
  @(negedge clk);write158=0;pre158=0;commit158=0;
 endtask
 initial begin
  unused155=$value$plusargs("CONTROL=%d",control155);
  if(control155)force dut.core.multi_mapper.game158_preview_write=0;
  $readmemh("prg.hex",prg);$readmemh("chr.hex",chr);
  force dut.core.ppu.cycle=dot158;force dut.core.ppu.scanline=9'd193;
  force dut.core.ppu.bg_patt1=bg158;force dut.core.ppu.is_rendering_d=render158;
  force dut.core.ppu.rendering_enabled=render158;force dut.core.ppu.bg_name_table=8'ha1;
  force dut.core.ppu.vram=15'd0;force dut.core.ppu.read_2007_delayed=0;force dut.core.ppu.write_2007_delayed=0;
  force dut.core.ppu.ce=ce158;force dut.core.ppu.read=0;force dut.core.ppu.write=0;force tap_ce=ce158;
  force dut.core.mw_int=write158;force dut.core.prg_addr=address158;force dut.core.prg_din=data158;
  force dut.core.cart_pre=pre158;force dut.core.cart_ce=commit158;
  force cpumem_addr=cpuaddr158;force cpumem_read=cpuread158;force rom_cpu_address_valid=cpuread158;
  force rom_cpu_sample=0;force cpumem_write=0;
  for(mode158=0;mode158<3;mode158=mode158+1)begin
  for(offset158=0;offset158<12;offset158=offset158+1)begin
   @(negedge clk);reset_request=1;render158=0;ce158=0;dot158=1;write158=0;cpuread158=0;bg158=0;
   repeat(8)@(negedge clk);reset_request=0;
   wait(!reset);wait(!dut.core.reset_noSS);wait(rom_ready);
   wr158(16'h8000,4);wr158(16'h8001,8'h5e);
   wr158(16'h8000,1);wr158(16'h8001,8'h16);
   failed158=0;requests158=0;checked158=0;render158=1;
   for(step158=0;step158<40;step158=step158+1)begin
    @(negedge clk);dot158=1+step158/4;ce158=(step158%4==3);
    cpuread158=(step158>=8+offset158 && step158<20);
    if(step158==20 && mode158<2)begin write158=1;address158=mode158==0?16'h8001:16'h8000;data158=mode158==0?8'h5e:8'h80;end
    pre158=write158 && step158>=25 && step158<=29;commit158=(step158==29);
    if(step158==30)begin write158=0;pre158=0;if(mode158==2)bg158=1;end
    @(posedge clk);
    if(rom_request)requests158++;
    if(rom_request || rom_response || fault_trigger || step158>=28)
     $display("TRACE158 mode=%0d step=%0d dot=%0d ppu=%h hint=%b/%h req=%b/%h resp=%b valid=%b busy=%b fault=%b",mode158,step158,dot158,ppumem_addr,game147_prefetch_hint,game148_hint_physical,rom_request,rom_address,rom_response,rom_ppu_valid,rom_service.busy,fault_trigger);
    if(fault_trigger)failed158=1;
    if(!failed158 && ce158 && ppumem_read && ppumem_addr>=22'h200000 && ppumem_addr<22'h220000)begin
     if(!rom_ppu_valid || ppumem_din!==chr[ppumem_addr[16:0]])$fatal(1,"wrong PPU byte");
     checked158++;
    end
    if(step158==28 && mode158<2 && ppumem_addr!==22'h205a18)$fatal(1,"mapper changed early");
    if(step158==30 && mode158<2 && ppumem_addr!==22'h217a18)$fatal(1,"mapper did not commit");
   end
   $display("CASE158 mode=%0d control=%0d failed=%0d error=%0d checked=%0d requests=%0d offset=%0d",mode158,control155,failed158,rom_error_code,checked158,requests158,offset158);
  end
  end
  $display("DONE158");$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog158");end
endmodule
