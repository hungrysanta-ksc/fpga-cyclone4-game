// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module diag_memory_timing_tb;
 reg mem_clk=0,clock_enable=1; always #62.5 if(clock_enable)mem_clk=~mem_clk;
 wire clk=mem_clk;
 reg reset=1,read_reset=1,load_begin=0,load_chr32=0,load_valid=0,load_end=0,start=0,stop=0;
 reg[7:0]load_data=0;
 reg check_enable=0,check_request=0;reg[16:0]check_address=0;
 wire load_ready,loaded,run_enable,boot_fault,rom_chr32,check_ready,check_response,check_fault;
 wire[3:0]boot_error;wire[16:0]loaded_bytes,check_response_address;wire[7:0]check_data;
 wire[21:0]psram_address;wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;
 tri[15:0]psram_data,pad_data;
 nes_rom_boot dut(.*,.rom_request(1'b0),.rom_address(22'd0),.rom_ready(),.rom_response(),
 .rom_error(),.rom_response_address(),.rom_data());
 integer ad=0,cd=0,dd=0,dq=0,hz=8,total=81920;
 wire[21:0]pa;wire c1,c2,oe,we,bhe,ble;
 assign #(ad) pa=psram_address;
 assign #(cd) c1=psram_1ce;assign #(cd) c2=psram_2ce;
 assign #(cd) oe=psram_oe;assign #(cd) we=psram_we;
 assign #(cd) bhe=psram_bhe;assign #(cd) ble=psram_ble;
 // Split the bidirectional IO into independent drive and receive delays.
 // Delays are sensitivity assumptions, not routed or measured board values.
 wire drive=!reset&&!dut.reader_owner&&dut.load_drive;
 assign #(dd) pad_data=drive?dut.load_pin_data:16'hzzzz;
 reg[15:0] memory[0:2097151];
 wire selected=(!c1||!c2);
 wire[20:0]index={!c2,pa[19:0]};
 assign #(70,70,hz) pad_data=(selected&&!oe&&we)?memory[index]:16'hzzzz;
 assign #(dq) psram_data=dut.reader_owner?pad_data:16'hzzzz;
 integer write_tag=0,read_tag=0,writes=0,reads=0,cancels=0;
 realtime last_data=0,we_start=0,ce_start=0,sample_time=-100000;
 reg read_cycle=0;
 function automatic[7:0] pattern(input integer i);
  pattern=8'((i*73)^(i>>8)^8'hb5);
 endfunction
 function automatic[21:0] address_of(input integer i);
  address_of=22'((i>=65536?22'h200000+(i-65536):i)>>2);
 endfunction
 always @(pad_data)last_data=$realtime;
 always @(posedge mem_clk)
  if(!reset&&dut.reader.state==2&&dut.reader.remaining==1)sample_time=$realtime;
 always @(negedge c1 or negedge c2) if(!reset)begin
  ce_start=$realtime;#0.002;
  if(!c1&&!c2)$fatal(1,"CHIP_OVERLAP");
  read_cycle=!oe;
  if(pa!==address_of(read_cycle?read_tag:write_tag))
   $fatal(1,"ADDRESS_SETUP_AT_CE read=%0d tag=%0d got=%h",read_cycle,read_cycle?read_tag:write_tag,pa);
 end
 always @(negedge we) if(!reset)begin we_start=$realtime;end
 always @(posedge we) if(!reset&&selected)begin
  if($realtime-we_start<46)$fatal(1,"WRITE_PULSE");
  if($realtime-last_data<23)$fatal(1,"WRITE_DATA_SETUP");
  if(pa!==address_of(write_tag))$fatal(1,"WRITE_ADDRESS");
  if(bhe!==1'b0&&ble!==1'b0)$fatal(1,"WRITE_LANES");
  if(!bhe)begin
   if(pad_data[15:8]!==pattern(write_tag))$fatal(1,"WRITE_DATA_HIGH");
   memory[index][15:8]=pad_data[15:8];
  end
  if(!ble)begin
   if(pad_data[7:0]!==pattern(write_tag))$fatal(1,"WRITE_DATA_LOW");
   memory[index][7:0]=pad_data[7:0];
  end
  writes=writes+1;
 end
 always @(posedge c1 or posedge c2) if(!reset&&$time>1000)begin
  if($realtime-ce_start>8000)$fatal(1,"CE_MAX_WIDTH");
  if(read_cycle)begin
   if($realtime-sample_time<124.999)$fatal(1,"READ_SAMPLE_HOLD");
   reads=reads+1;read_cycle=0;
  end
 end
 task automatic pulse_begin;
  @(negedge mem_clk);load_begin=1;@(negedge mem_clk);load_begin=0;
 endtask
 task automatic put_byte(input integer tag);
  wait(load_ready);@(negedge mem_clk);write_tag=tag;load_data=pattern(tag);load_valid=1;
  @(negedge mem_clk);load_valid=0;
 endtask
 task automatic get_byte(input integer tag);
  wait(check_ready);@(negedge mem_clk);read_tag=tag;check_address=17'(tag);check_request=1;
  @(negedge mem_clk);check_request=0;
  wait(check_response);
  if(check_response_address!==17'(tag)||check_data!==pattern(tag))
   $fatal(1,"READ_CONTENT tag=%0d got=%h expected=%h",tag,check_data,pattern(tag));
  if(!psram_1ce||!psram_2ce||!psram_oe)$fatal(1,"RESPONSE_BEFORE_RELEASE");
  @(negedge mem_clk);
 endtask
 task automatic reset_stopped;
  // Reset while both functional clocks are stopped must still release pins.
  clock_enable=0;reset=1;#40;
  if(!c1||!c2||!oe||!we||pad_data!==16'hzzzz||load_ready||check_ready||loaded||run_enable)
   $fatal(1,"STOPPED_RESET_RELEASE");
  load_begin=0;load_valid=0;load_end=0;stop=0;check_enable=0;check_request=0;
  read_cycle=0;cancels=cancels+1;clock_enable=1;
  repeat(3)@(negedge mem_clk);reset=0;repeat(4)@(negedge mem_clk);
 endtask
 initial begin
  if(!$value$plusargs("AD=%d",ad))ad=0;
  if(!$value$plusargs("CD=%d",cd))cd=0;
  if(!$value$plusargs("DD=%d",dd))dd=0;
  if(!$value$plusargs("DQ=%d",dq))dq=0;
  if(!$value$plusargs("HZ=%d",hz))hz=8;
  if(!$value$plusargs("TOTAL=%d",total))total=81920;
  if(total!=81920&&total!=98304)$fatal(1,"GEOMETRY");
  load_chr32=(total==98304);
  repeat(4)@(negedge mem_clk);reset=0;repeat(4)@(negedge mem_clk);
  pulse_begin();
  for(integer i=0;i<total;i=i+1)put_byte(i);
  wait(loaded_bytes==total);@(negedge mem_clk);load_end=1;@(negedge mem_clk);load_end=0;
  if(!loaded||boot_fault||rom_chr32!==load_chr32)$fatal(1,"LOAD_COMPLETION");
  check_enable=1;
  for(integer i=0;i<total;i=i+1)get_byte(i);
  if(check_fault||writes!=total||reads!=total)$fatal(1,"COVERAGE");
  $display("FULL_MEMORY total=%0d writes=%0d reads=%0d",total,writes,reads);
  check_enable=0;@(negedge mem_clk);stop=1;@(negedge mem_clk);stop=0;
  // Normal protocol error while WE is active must drain WRITE and HOLD.
  pulse_begin();put_byte(0);wait(dut.loader.state==2);@(negedge mem_clk);stop=1;
  @(negedge mem_clk);stop=0;repeat(8)@(negedge mem_clk);
  if(!boot_fault||boot_error!=6||loaded||!psram_we||!psram_1ce||!psram_2ce)
   $fatal(1,"FAULT_DRAIN");
  reset_stopped();
  // Cancellation in every new write phase, using normal loader handshakes.
  for(integer k=0;k<4;k=k+1)begin
   pulse_begin();put_byte(0);
   case(k)
    0:wait(dut.loader.state==7);
    1:wait(dut.loader.state==2);
    2:wait(dut.loader.state==3);
    3:wait(dut.loader.state==8);
   endcase
   #1;reset_stopped();
  end
  // Read phase cancellation uses READY-state fault injection only to avoid
  // reloading80KiB for each abort. It is distinct from the full normal transfer.
  for(integer k=1;k<=4;k=k+1)begin
   force dut.loader.state=4'd4;#1;release dut.loader.state;
   check_enable=1;wait(check_ready);@(negedge mem_clk);
   read_tag=28;check_address=28;check_request=1;
   @(negedge mem_clk);check_request=0;wait(dut.reader.state==k);
   #1;reset_stopped();
  end
  $display("PASS_DIAG_MEMORY total=%0d ad=%0d cd=%0d dd=%0d dq=%0d hz=%0d cancels=%0d",total,ad,cd,dd,dq,hz,cancels);
  $finish;
 end
 initial begin #600000000.0;$fatal(1,"WATCHDOG");end
endmodule
