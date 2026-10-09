// SPDX-License-Identifier: MIT
// Changed write timing and actual boot ownership; synthetic RAM, not board timing.
`timescale 1ns/1ps
module loader127_tb;
 reg clk=0,mem_clk=0,reset=1,read_reset=1;
 always #22.727 clk=~clk;
 always #2.976 mem_clk=~mem_clk;
 reg load_begin=0,load_chr32=0,load_valid=0,load_end=0,start=0,stop=0;
 reg [7:0] load_data=0;
 wire load_ready,loaded,run_enable,boot_fault,rom_chr32;
 wire [3:0] boot_error;wire [16:0] loaded_bytes;
 reg check_enable=0,check_request=0;reg [16:0] check_address=0;
 wire check_ready,check_response,check_fault;wire [16:0] check_response_address;wire [7:0] check_data;
 reg rom_request=0;reg [21:0] rom_address=0;
 wire rom_ready,rom_response,rom_error;wire [21:0] rom_response_address;wire [7:0] rom_data;
 wire [21:0] psram_address;wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;
 tri [15:0] psram_data;
 nes_rom_boot dut(.*);rom_boot_model ram(.*);
 integer checks=0,writes=0,reads=0,run_reads=0,drains=0;
 realtime setup_at,write_at,hold_at,release_at;
 reg monitor_write=0;reg [21:0] held_address;reg [15:0] held_data;
 function automatic [7:0] pattern(input integer a);pattern=(a*73)^(a>>7)^(a>>13)^8'ha6;endfunction
 task automatic ck(input bit ok,input string why);checks++;if(!ok)$fatal(1,"LOADER127 %s count=%0d",why,checks);endtask
 always @(posedge dut.load_drive)if(!reset)begin
  ck($realtime-release_at>=125,"release below125ns");setup_at=$realtime;
 end
 always @(negedge psram_we)if(!reset)begin
  ck($realtime-setup_at>=125,"setup below125ns");write_at=$realtime;
  held_address=psram_address;held_data=psram_data;monitor_write=1;
 end
 always @(posedge psram_we)if(!reset && monitor_write)begin
  ck($realtime-write_at>=375,"write below375ns");hold_at=$realtime;writes++;
 end
 always @(negedge dut.load_drive)if(!reset && monitor_write)begin
  ck($realtime-hold_at>=125,"hold below125ns");release_at=$realtime;monitor_write=0;
 end
 always @(negedge mem_clk)if(!reset)begin
  ck(!(!psram_oe && dut.load_drive),"read/write collision");
  if(monitor_write)ck(psram_address===held_address && psram_data===held_data,"write/hold stability");
  if(run_enable)ck(psram_we,"RUN write prohibited");
 end
 task automatic fresh;
  @(negedge mem_clk);reset=1;monitor_write=0;check_enable=0;check_request=0;rom_request=0;
  load_begin=0;load_valid=0;load_end=0;start=0;stop=0;read_reset=1;
  repeat(5)@(negedge mem_clk);reset=0;repeat(30)@(negedge mem_clk);
 endtask
 task automatic begin_image;
  load_begin=1;@(negedge mem_clk);load_begin=0;
 endtask
 task automatic send_byte(input integer a);
  ck(load_ready,"load ready");load_valid=1;load_data=pattern(a);
  @(negedge mem_clk);load_valid=0;
  // Last byte deliberately has no ready; completion is the byte-count update.
  wait(loaded_bytes==a+1);@(negedge mem_clk);
 endtask
 task automatic check_byte(input integer a);
  wait(check_ready);@(negedge mem_clk);check_address=a;check_request=1;
  @(negedge mem_clk);check_request=0;check_address=~a;
  wait(check_response);#0.001;
  ck(check_response_address==a && check_data===pattern(a),"CHECK data/tag");
  ck(psram_we&&psram_oe&&!run_enable,"CHECK completes after release");reads++;
  @(negedge mem_clk);@(negedge mem_clk);
 endtask
 task automatic run_byte(input integer a);
  wait(rom_ready);@(negedge clk);rom_address=a>=65536?22'h200000+a-65536:a;rom_request=1;
  @(negedge clk);rom_request=0;wait(rom_response);#0.001;
  ck(rom_data===pattern(a)&&!rom_error,"RUN data");run_reads++;@(negedge clk);@(negedge clk);
 endtask
 initial begin
  integer total,before_writes;
  release_at=-1000;
  for(integer mode=0;mode<2;mode++)begin
   fresh();load_chr32=mode!=0;begin_image();total=mode?98304:81920;before_writes=ram.writes;
   for(integer a=0;a<total;a++)send_byte(a);
   ck(ram.writes-before_writes==total&&!loaded&&!boot_fault,"pin writes/length");
   load_end=1;@(negedge mem_clk);load_end=0;ck(loaded&&!run_enable,"loaded core held");
   check_enable=1;
   for(integer a=0;a<64;a++)begin check_byte(a);check_byte(65536+a);end
   check_byte(65535);check_byte(total-1);
   check_enable=0;repeat(5)@(negedge mem_clk);
   ck(psram_we&&psram_oe&&psram_1ce&&psram_2ce,"owner transition neutral");
   start=1;@(negedge mem_clk);start=0;read_reset=0;
   repeat(6)@(negedge clk);ck(run_enable&&!check_fault,"RUN ownership");
   for(integer a=0;a<32;a++)begin run_byte(a);run_byte(total-1-a);end
   @(negedge mem_clk);stop=1;@(negedge mem_clk);stop=0;read_reset=1;
   #0.001;ck(!run_enable&&loaded&&psram_oe&&psram_we,"STOP cancellation");
  end
  // Every position in WRITE/HOLD: a rejected STOP cannot truncate accepted data.
  for(integer phase=0;phase<86;phase++)begin
   fresh();load_chr32=0;begin_image();load_valid=1;load_data=pattern(0);
   @(negedge mem_clk);load_valid=0;wait(!psram_we);
   repeat(phase)@(negedge mem_clk);@(negedge mem_clk);stop=1;
   @(negedge mem_clk);stop=0;repeat(140)@(negedge mem_clk);
   ck(boot_fault&&!run_enable&&!load_ready&&psram_we&&psram_oe,"sticky fault drained");drains++;
  end
  // CHECK misuse while writing cancels reads, but drains the accepted write.
  fresh();begin_image();load_valid=1;load_data=pattern(0);@(negedge mem_clk);load_valid=0;
  wait(!psram_we);@(negedge mem_clk);check_enable=1;repeat(140)@(negedge mem_clk);
  ck(check_fault&&!run_enable&&psram_we&&psram_oe,"CHECK fault drain");
  $display("PASS127 LOADER pin_writes=%0d check_reads=%0d run_reads=%0d drains=%0d",writes,reads,run_reads,drains);$finish;
 end
 initial begin #200000000;$fatal(1,"LOADER127 watchdog");end
endmodule
