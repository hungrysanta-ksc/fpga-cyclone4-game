// SPDX-License-Identifier: MIT
// Public synthetic bytes, actual pin writes/read model; not board evidence.
`timescale 1ns/1ps
module rom_readback_tb;
 reg clk=0,mem_clk=0,reset=1,read_reset=1;
 always #23.280423 clk=~clk;
 always #5.952381 mem_clk=~mem_clk;
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
 nes_rom_boot dut(.*);
 rom_boot_model ram(.*);
 integer checks=0,loaded_total=0,read_total=0,run_reads=0,cancels=0,rejected=0,corruptions=0;
 function automatic [7:0] pattern(input integer a);
  pattern=(a*73)^(a>>7)^(a>>13)^8'ha6;
 endfunction
 task automatic ck(input bit ok,input string message);
  checks++;if(!ok)$fatal(1,"READBACK check%0d %s",checks,message);
 endtask
 task automatic fresh;
  @(negedge mem_clk);reset=1;check_enable=0;check_request=0;rom_request=0;
  load_begin=0;load_valid=0;load_end=0;start=0;stop=0;read_reset=1;
  repeat(5)@(negedge mem_clk);reset=0;repeat(6)@(negedge mem_clk);
  ck(!run_enable&&!loaded&&!check_fault&&!check_response,"reset");
 endtask
 task automatic load_image(input bit mode);
  integer total,writes_before;
  total=mode?98304:81920;writes_before=ram.writes;
  load_chr32=mode;load_begin=1;@(negedge mem_clk);load_begin=0;
  for(integer a=0;a<total;a++)begin
   ck(load_ready,"load ready");load_valid=1;load_data=pattern(a);
   @(negedge mem_clk);load_valid=0;repeat(5)@(negedge mem_clk);
  end
  ck(loaded_bytes==total&&!boot_fault&&!loaded,"pre END");
  load_end=1;@(negedge mem_clk);load_end=0;
  ck(loaded&&!run_enable&&rom_chr32===mode,"END");
  ck(ram.writes-writes_before==total,"actual pin write count");loaded_total+=total;
 endtask
 task automatic open_check;
  check_enable=1;repeat(5)@(negedge mem_clk);
  ck(check_ready&&!check_fault&&!run_enable,"CHECK while core held reset");
 endtask
 task automatic read_byte(input integer a,input bit expect_match);
  integer timeout;reg [7:0] got;
  ck(check_ready,"read ready");check_address=a;check_request=1;
  @(negedge mem_clk);check_request=0;
  // A later command can overwrite its input. Accepted address must be held.
  check_address=~a;timeout=0;
  while(!check_response && timeout<12)begin @(negedge mem_clk);timeout++;end
  ck(check_response&&!check_fault,"bounded completion");
  ck(check_response_address==a,"returned accepted address tag");
  got=check_data;ck((got===pattern(a))==expect_match,"returned pin data");
  ck(!run_enable&&read_reset&&!rom_response&&psram_we,"core stopped/no write");
  read_total++;@(negedge mem_clk);ck(!check_response,"no repeated completion");
 endtask
 task automatic run_read(input integer a);
  integer timeout;reg [21:0] pa;
  pa=a>=65536?22'h200000+a-65536:a;
  @(negedge clk);ck(rom_ready,"RUN ready");rom_address=pa;rom_request=1;
  @(negedge clk);rom_request=0;rom_address=~pa;timeout=0;
  while(!rom_response&&timeout<12)begin @(negedge clk);timeout++;end
  ck(rom_response&&!rom_error&&rom_response_address==pa&&rom_data===pattern(a),"RUN data/tag");
  run_reads++;@(negedge clk);
 endtask
 initial begin
  integer total,a,writes_before;
  for(integer mode=0;mode<2;mode++)begin
   fresh();load_image(mode!=0);total=mode?98304:81920;open_check();
   for(a=0;a<total;a++)read_byte(a,1);
   // Data corruption is visible to the caller; FPGA does not claim a CRC verdict.
   ram.prg[17]^=8'h01;read_byte(17,0);ram.prg[17]^=8'h01;corruptions++;
   ram.chr[123]^=8'h80;read_byte(65536+123,0);ram.chr[123]^=8'h80;corruptions++;
   // Cancel at each controller phase, then reopen without stale completion.
   for(integer phase=0;phase<4;phase++)begin
    check_address=phase+12;check_request=1;@(negedge mem_clk);check_request=0;
    repeat(phase)@(negedge mem_clk);check_enable=0;
    repeat(5)@(negedge mem_clk);ck(!check_response&&!check_fault&&psram_oe,"cancel idle");
    open_check();ck(!check_response,"no stale reply");read_byte(65540+phase,1);cancels++;
   end
   check_enable=0;repeat(5)@(negedge mem_clk);
   start=1;@(negedge mem_clk);start=0;read_reset=0;
   repeat(5)@(negedge clk);ck(run_enable&&!check_fault,"CHECK to RUN");
   for(a=0;a<256;a++)begin run_read(a);run_read(65536+(a*61)%(total-65536));end
   @(negedge mem_clk);stop=1;@(negedge mem_clk);stop=0;read_reset=1;
   ck(!run_enable&&loaded,"RUN stop retains image");open_check();read_byte(total-1,1);
   // Invalid range must not be sent to the physical bus.
   check_address=total;check_request=1;@(negedge mem_clk);check_request=0;
   ck(check_fault&&!run_enable&&!check_response&&psram_oe,"range reject");rejected++;
  end
  for(integer bad=0;bad<6;bad++)begin
   fresh();load_image(0);open_check();
   case(bad)
    0:begin check_address=3;check_request=1;@(negedge mem_clk);check_address=9;end // second while busy
    1:start=1;
    2:load_begin=1;
    3:load_valid=1;
    4:load_end=1;
    5:begin check_enable=0;check_request=1;end
   endcase
   @(negedge mem_clk);check_request=0;start=0;load_begin=0;load_valid=0;load_end=0;
   ck(check_fault&&!run_enable&&!check_response&&psram_we,"illegal overlap blocked");
   repeat(6)@(negedge mem_clk);ck(!check_response&&psram_oe,"fault cancels read");rejected++;
  end
  fresh();load_image(0);open_check();check_address=123;check_request=1;
  @(negedge mem_clk);check_request=0;stop=1;check_enable=0;
  @(negedge mem_clk);stop=0;repeat(5)@(negedge mem_clk);
  ck(!loaded&&!run_enable&&!check_fault&&!check_response&&psram_oe,"STOP cancels and invalidates CHECK");cancels++;
  fresh();load_image(0);open_check();check_request=1;
  @(negedge mem_clk);reset=1;check_enable=0;check_request=0;
  #1;ck(!check_response&&!run_enable&&psram_oe&&psram_we,"common reset cancels immediately");cancels++;
  fresh();check_enable=1;@(negedge mem_clk);ck(check_fault&&!run_enable,"unloaded CHECK rejected");rejected++;
  // CHECK misuse must not shorten a write that the loader already accepted.
  fresh();writes_before=ram.writes;load_begin=1;@(negedge mem_clk);load_begin=0;
  load_valid=1;load_data=pattern(0);@(negedge mem_clk);load_valid=0;check_enable=1;
  @(negedge mem_clk);ck(check_fault&&!psram_we,"fault preserves active write pulse");
  repeat(6)@(negedge mem_clk);
  ck(ram.writes==writes_before+1&&ram.prg[0]===pattern(0)&&psram_we&&psram_oe,"accepted write drained");
  loaded_total++;rejected++;
  $display("PASS READBACK PORT checks=%0d pin_written_bytes=%0d checked_reads=%0d run_reads=%0d cancellations=%0d rejected=%0d corruptions_detected=%0d",checks,loaded_total,read_total,run_reads,cancels,rejected,corruptions);
  $finish;
 end
 initial begin #200000000;$fatal(1,"READBACK watchdog");end
endmodule
