// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module owner562_tb;
 reg clk=0,mem_clk=0,reset=1;
 bit shift_once=0;
 always begin #23281;if(shift_once)begin #3100;shift_once=0;end clk=!clk;end
 always #2976 mem_clk=!mem_clk;
 reg load_begin=0,load_valid=0,load_end=0,start=0,stop=0,check_enable=0,check_request=0;
 reg [7:0] load_data;reg [18:0] check_address;wire [18:0] check_response_address,loaded_bytes;
 wire check_ready,check_response,check_fault,loaded,run_enable,load_ready,boot_fault;
 wire [7:0] check_data,rom_data;wire [3:0] boot_error;
 wire reset_request,memory_ready,core_reset;wire raw_stop=reset||!run_enable;
 wire common_reset=raw_stop||!memory_ready;
 nes_domain_reset124 init_release(clk,raw_stop,reset_request);
 nes_domain_reset124 core_release(clk,common_reset,core_reset);
 nes_local_memory local_memory(.clk(clk),.reset(reset_request),.init_done(memory_ready),
  .native_nt_address(11'd0),.cpumem_addr(25'd0),.cpumem_write(1'b0),.cpumem_dout(8'd0),
  .ppumem_addr(22'd0),.ppumem_write(1'b0),.ppumem_dout(8'd0),.external_cpu_data(8'd0),.external_ppu_data(8'd0));
 reg request=0;reg [21:0] rom_address;
 wire raw_ready,rom_response,rom_error;wire [21:0] rom_response_address;
`ifdef OWNER562
 wire read_reset=raw_stop,rom_request=request&&!core_reset,rom_ready=raw_ready&&!core_reset;
`else
 wire read_reset=common_reset,rom_request=request,rom_ready=raw_ready;
`endif
 wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;
 wire [21:0] psram_address;wire [15:0] psram_data;
 nes_rom_boot dut(.rom_ready(raw_ready),.load_chr32(1'b0),.rom_chr32(),.*);
 rom_boot_model memory(.*);
 function automatic [7:0] pattern(input [18:0] i);
  return i[7:0]^i[15:8]^{5'd0,i[18:16]}^8'h69;
 endfunction
 function automatic [21:0] physical(input [18:0] i);
  return i[18]?(22'h200000+{4'b0,i[17:0]}):{3'd0,i};
 endfunction
 integer responses=0,scrubs=0,frames=0,fd,accepted=0;longint epoch_ps,target_ps;integer linear,offset,code;
 always @(posedge clk)if(!core_reset)begin
  if(request&&rom_ready)begin accepted++;$display("ACCEPT562 %0d %0t %h",accepted,$time,rom_address);end
  if(rom_response)begin responses++;$display("REPLY562 %0d %0t %h %h",responses,$time,rom_response_address,rom_data);end
 end
 always @(negedge mem_clk)if(!reset)begin
  if(run_enable && core_reset && (!psram_oe||!psram_we||!psram_1ce||!psram_2ce))$fatal(1,"PSRAM used during scrub");
  if(boot_fault||check_fault||rom_error)$fatal(1,"unexpected fault");
 end
 task command_start;
  @(negedge mem_clk);start=1;@(negedge mem_clk);start=0;
  if(!run_enable)$fatal(1,"START");
 endtask
 task check_byte(input [18:0] at);
  @(negedge mem_clk);while(!check_ready)@(negedge mem_clk);
  check_address=at;check_request=1;@(negedge mem_clk);check_request=0;
  while(!check_response)@(negedge mem_clk);
  if(check_response_address!==at||check_data!==pattern(at))$fatal(1,"CHECK %h %h",at,check_data);
 endtask
 task receive_byte(input [18:0] at);
  while(!rom_response)@(negedge clk);
  if(rom_response_address!==physical(at)||rom_data!==pattern(at))$fatal(1,"RUN data");
  @(negedge clk);if(rom_response)$fatal(1,"duplicate reply");
 endtask
 task read_byte(input [18:0] at);
  @(negedge clk);while(!rom_ready)@(negedge clk);
  request=1;rom_address=physical(at);@(negedge clk);request=0;receive_byte(at);
 endtask
 task scrub_read(input [18:0] at);
  integer cycles;cycles=0;rom_address=physical(at);request=1;
  @(negedge clk);while(!rom_ready)begin
    if(!memory_ready&&!reset_request)cycles++;
    if(rom_response)$fatal(1,"stale reply during scrub");@(negedge clk);
  end
  if(cycles!=8192||core_reset)$fatal(1,"scrub cycles %0d",cycles);
  @(negedge clk);request=0;receive_byte(at);scrubs++;
 endtask
 task stop_reader;
  @(negedge mem_clk);stop=1;@(negedge mem_clk);stop=0;
  if(run_enable||!loaded||!psram_oe||!psram_we||!psram_1ce||!psram_2ce)$fatal(1,"STOP pins");
  repeat(10)begin @(negedge clk);if(rom_response||!core_reset)$fatal(1,"reply after STOP");end
 endtask
 initial begin
  #70000;reset=0;repeat(8)@(negedge mem_clk);load_begin=1;@(negedge mem_clk);load_begin=0;
  for(int i=0;i<'h60000;i++)begin
   // Fast bench self-test only. The selected run drives every byte over pins.
   if(i==1 && $test$plusargs("SMOKE"))begin
    while(!load_ready)@(negedge mem_clk);
    for(int j=1;j<'h5ffff;j++)begin
     if(j<'h40000)memory.prg[j]=pattern(j);else memory.chr[j-'h40000]=pattern(j);
    end
    i='h5ffff;dut.loader.loaded_bytes=i;
   end
   while(!load_ready)@(negedge mem_clk);load_data=pattern(i);load_valid=1;@(negedge mem_clk);load_valid=0;
  end
  // At the terminal count no additional data credit is issued.
  while(loaded_bytes!==19'h60000)@(negedge mem_clk);load_end=1;@(negedge mem_clk);load_end=0;
  if(!loaded||memory.writes!=($test$plusargs("SMOKE")?2:'h60000)||loaded_bytes!='h60000)$fatal(1,"incomplete PSRAM load");
  for(int phase=1;phase<=2;phase++)begin
  if(phase==2)begin shift_once=1;wait(!shift_once);end
  $display("PHASE562 %0d",phase);
  check_enable=1;rom_address=22'h77;request=1;
  check_byte(0);check_byte('h3ffff);check_byte('h40000);check_byte('h5ffff);
  if(dut.reader.request_toggle!==0||rom_response)$fatal(1,"NES request accepted in CHECK");
  request=0;@(negedge mem_clk);check_enable=0;repeat(6)@(negedge mem_clk);
  command_start();scrub_read('h40001);
  // A live physical read is canceled before the memory sample edge.
  @(negedge clk);request=1;rom_address=22'h8;@(negedge clk);request=0;wait(!psram_oe);stop_reader();
  check_enable=1;check_byte('h40000);@(negedge mem_clk);check_enable=0;repeat(6)@(negedge mem_clk);
  command_start();scrub_read(9);
  fd=$fopen($sformatf("reads%0d.txt",phase),"r");if(!fd)$fatal(1,"missing trace");epoch_ps=$time;
  while(!$feof(fd))begin
   code=$fscanf(fd,"%d %d\n",offset,linear);
   if(code==2)begin target_ps=epoch_ps+longint'(offset)*46562;
    if(!$test$plusargs("SMOKE") && $time<target_ps)#(target_ps-$time);
    read_byte(linear);frames++;
   end
  end
  $fclose(fd);stop_reader();
  if(frames==0||responses!=frames+2*phase||accepted!=responses+phase)$fatal(1,"request ledger");
  $display("PASS562 phase=%0d total_reads=%0d scrubs=%0d writes=%0d",phase,frames,scrubs,memory.writes);
  end
  $finish;
 end
 initial begin #(64'd2000000000000);$fatal(1,"timeout");end
endmodule
