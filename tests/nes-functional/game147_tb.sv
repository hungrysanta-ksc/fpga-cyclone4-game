// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module game147_tb;
 reg clk=0,mem_clk=0,reset_request=1;
 always #23.280423 clk=~clk;
 initial begin #3.5;forever #2.9761905 mem_clk=~mem_clk;end
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
 wire rom_cpu_address_valid,rom_ppu_address_valid,rom_cpu_sample;
 nes_probe dut(.*);
 wire [7:0] external_cpu_data,external_ppu_data;
 wire rom_cpu_valid,rom_ppu_valid,rom_fault;
 wire [3:0] rom_error_code;wire [63:0] fault_context;wire fault_trigger;
 wire rom_ready,rom_request,rom_response,rom_error;
 wire [21:0] rom_address,rom_response_address;wire [7:0] rom_data;
 nes_rom_early rom_service(
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
 integer target,unused,frame=0,fp=0,pixels=0,ticks=0,cpu_reads=0,ppu_reads=0,mapper_writes=0,irq_edges=0;
 reg [31:0] prg_banks=0;reg [127:0] chr_banks=0;
 reg [8:0] prevcycle=511,prevline=511;
 reg prior_irq=0;reg [63:0] first_context=0;
 reg [255:0] history[0:15];integer hi=0;
 always @(posedge clk)if(!reset)begin
  history[hi]<={ticks,cpumem_addr,ppumem_addr,cycle,scanline,rom_address,rom_response_address,
   rom_cpu_sample,tap_ce,ppumem_read,rom_ppu_address_valid,rom_cpu_valid,rom_ppu_valid,
   rom_request,rom_response,rom_service.pending_ppu,rom_service.busy,
   rom_service.ppu_tag,rom_service.ppu_previous_tag,rom_data,external_ppu_data};
  hi<=(hi+1)%16;
 end
 always @(posedge clk)if(!reset)begin
  ticks++;
  if(fault_trigger && first_context==0)first_context<=fault_context;
  if(rom_fault)$fatal(1,"GAME147 ROM error=%0d tick=%0d frame=%0d cpu=%h ppu=%h context=%h",rom_error_code,ticks,frame,cpumem_addr,ppumem_addr,first_context);
  if(rom_cpu_sample && cpumem_addr<25'h40000)begin
   if(!rom_cpu_valid || cpumem_din!==prg[cpumem_addr])$fatal(1,"CPU ROM byte mismatch addr=%h got=%h",cpumem_addr,cpumem_din);
   cpu_reads++;prg_banks[cpumem_addr[17:13]]=1;
  end
  if(tap_ce && ppumem_read && ppumem_addr>=22'h200000 && ppumem_addr<22'h220000)begin
   if(!rom_ppu_valid || ppumem_din!==chr[ppumem_addr[16:0]])begin
    for(integer h=0;h<16;h++)$display("HISTORY147 %064h",history[(hi+h)%16]);
    $display("PPU147 frame=%0d line=%0d dot=%0d valid=%b expected=%h actual=%h cached=%b/%h/%h previous=%b/%h/%h reply=%b/%h/%h fault=%b context=%h",
     frame,scanline,cycle,rom_ppu_valid,chr[ppumem_addr[16:0]],ppumem_din,
     rom_service.ppu_cached,rom_service.ppu_tag,rom_service.ppu_byte,rom_service.ppu_previous_cached,rom_service.ppu_previous_tag,rom_service.ppu_previous_byte,
     rom_response,rom_response_address,rom_data,fault_trigger,fault_context);
    $fatal(1,"PPU ROM byte mismatch addr=%h got=%h",ppumem_addr,ppumem_din);
   end
   ppu_reads++;chr_banks[ppumem_addr[16:10]]=1;
  end
  if(tap_mapper_change)mapper_writes++;
 end
 always @(negedge clk)begin
  if(!reset && (cycle!=prevcycle || scanline!=prevline))begin
   if(scanline==0 && cycle==2)begin
    frame++;pixels=0;
    if(frame<=2 || frame%10==0 || frame==target)fp=$fopen($sformatf("game-%0d.hex",frame),"w");
   end
   if(frame>0 && scanline<240 && cycle>=2 && cycle<=257)begin
    if($isunknown({color,emphasis}))$fatal(1,"Unknown output pixel");
    if(fp)$fwrite(fp,"%03x\n",{emphasis,color});pixels++;
   end
   if(frame>0 && scanline==240 && cycle==1)begin
    if(pixels!=61440)$fatal(1,"Incomplete NES picture %0d",pixels);
    if(fp)begin $fclose(fp);fp=0;end
    if(frame%10==0)$display("GAME147 frame=%0d ticks=%0d cpu=%0d ppu=%0d banks=%h/%h mapper=%0d",frame,ticks,cpu_reads,ppu_reads,prg_banks,chr_banks,mapper_writes);
    if(frame==target)begin
     if(cpu_reads<1000 || !(prg_banks[31]) || mapper_writes==0)$fatal(1,"Game boot coverage absent");
     $display("PASS GAME147 frames=%0d cpu=%0d ppu=%0d prg_banks=%h chr_banks=%h mapper=%0d",frame,cpu_reads,ppu_reads,prg_banks,chr_banks,mapper_writes);$finish;
    end
   end
  end
  prevcycle=cycle;prevline=scanline;
 end
 initial begin
  unused=$value$plusargs("FRAMES=%d",target);if(!unused)target=120;
  $readmemh("prg.hex",prg);$readmemh("chr.hex",chr);
  #20000;reset_request=0;
  #(20000000.0*(target+2));$fatal(1,"GAME147 watchdog");
 end
endmodule
