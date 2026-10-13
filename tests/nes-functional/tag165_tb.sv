// SPDX-License-Identifier: MIT
// Actual SPI + boot + READ16 reader. Only loader count/READY and idle CHECK
// counters are seeded; no full ROM write or game boot is claimed.
`timescale 1ns/1ps
module tag165_tb;
 reg clk=0,mem_clk=0,reset=1;
 always #23.280423 clk=~clk;
 always #2.9761905 mem_clk=~mem_clk;
 reg SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 wire load_begin,load_chr32,load_valid,load_end,start,stop;
 wire [7:0] load_data,check_data;
 wire load_ready,loaded,run_enable,boot_fault,check_enable,check_request,check_ready,raw_response,raw_fault;
 wire [3:0] boot_error;wire [18:0] loaded_bytes,check_address,raw_address;
 reg inject_fault=0;reg [18:0] bad_mask=0;
 wire check_fault=raw_fault||inject_fault;
 wire check_response=raw_response;
 // Corrupt at the response itself, without a prior-cycle stable-address
 // assumption. The request-tag comparison must still reject every bit.
 wire [18:0] check_response_address=raw_address^(raw_response?bad_mask:19'd0);
 wire fault;wire [3:0] error_code;
 nes_rom_spi_check dut(.*,.spi_miso(),.spi_selected());
 baseline_check165 refdut(.mem_clk(mem_clk),.reset(reset),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
 .load_ready(load_ready),.loaded(loaded),.run_enable(run_enable),.boot_fault(boot_fault),.boot_error(boot_error),
 .loaded_bytes(loaded_bytes),.check_ready(check_ready),.check_response(check_response),.check_fault(check_fault),
 .check_response_address(check_response_address),.check_data(check_data));
 wire [21:0] psram_address;wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;
 wire [15:0] psram_data;
 assign #70 psram_data=!psram_oe?16'h1234:16'hzzzz;
 nes_rom_boot boot(.clk(clk),.mem_clk(mem_clk),.reset(reset),.read_reset(1'b1),
 .check_enable(check_enable),.check_request(check_request),.check_address(check_address),.check_ready(check_ready),
 .check_response(raw_response),.check_response_address(raw_address),.check_data(check_data),.check_fault(raw_fault),
 .load_begin(load_begin),.load_chr32(load_chr32),.load_valid(load_valid),.load_end(load_end),.start(start),.stop(stop),.load_data(load_data),
 .load_ready(load_ready),.loaded(loaded),.run_enable(run_enable),.boot_fault(boot_fault),.boot_error(boot_error),.loaded_bytes(loaded_bytes),
 .rom_chr32(),.rom_request(1'b0),.rom_address(22'd0),.rom_ready(),.rom_response(),.rom_error(),.rom_response_address(),.rom_data(),
 .psram_address(psram_address),.psram_1ce(psram_1ce),.psram_2ce(psram_2ce),.psram_oe(psram_oe),.psram_we(psram_we),
 .psram_bhe(psram_bhe),.psram_ble(psram_ble),.psram_data(psram_data));
 integer edges=0,reads=0,acks=0,cancels=0,corruptions=0,overlaps=0;
 // Expanded by the Python runner to compare every pre-existing SPI register.
 always @(negedge mem_clk)begin
  #0.01;
  if(!reset)begin
   edges++;
   // COMPARE_ALL_REGISTERS
   if(dut.check_busy && dut.check_request_tag!==dut.check_next)$fatal(1,"TAG165 invariant busy tag/counter");
  end
 end
 task tick;@(negedge mem_clk);#0.1;endtask
 task fresh;
  tick();reset=1;SPI_SS=1;SPI_SCK=0;inject_fault=0;bad_mask=0;
  repeat(5)tick();reset=0;repeat(8)tick();
  boot.loader.state=4;boot.loader.loaded_bytes=19'h60000;boot.loader.count_complete=1;
  repeat(4)tick();
 endtask
 function automatic [7:0] crc_byte(input [7:0] p,input [7:0] v);
  reg [7:0] c;c=p^v;repeat(8)c=c[7]?(c<<1)^8'h07:c<<1;return c;
 endfunction
 task frame(input [7:0] op,input [23:0] offset,input [7:0] arg);
  reg [7:0] tx[0:7];reg [7:0] c;
  tx[0]=op;tx[1]=offset[23:16];tx[2]=offset[15:8];tx[3]=offset[7:0];tx[4]=arg;tx[5]=~arg;
  c=0;for(integer k=0;k<6;k++)c=crc_byte(c,tx[k]);tx[6]=c;tx[7]=8'ha5;
  SPI_SS=0;#2000;
  for(integer j=0;j<64;j++)begin SPI_MOSI=tx[j/8][7-j%8];#190.476;SPI_SCK=1;#190.476;SPI_SCK=0;end
  #2000;SPI_SS=1;
 endtask
 task begin_check(input [18:0] n);
  fresh();frame(8'h66,0,0);repeat(12)tick();
  if(fault||!check_enable||!check_ready)$fatal(1,"TAG165 begin");
  dut.check_next=n;refdut.check_next=n;repeat(4)tick();
 endtask
 task request;
  frame(8'h67,{5'd0,check_address},0);wait(check_request);tick();reads++;
 endtask
 task normal(input [18:0] n);
  begin_check(n);request();repeat(26)tick();
  if(fault||!dut.check_done||dut.checked_data!==(n[0]?8'h34:8'h12))$fatal(1,"TAG165 normal response");
  frame(8'h68,{5'd0,n},dut.checked_data);repeat(12)tick();
  if(fault||check_address!==n+19'd1||dut.check_busy||dut.check_done)$fatal(1,"TAG165 ACK");acks++;
  frame(8'h64,24'h60000,0);repeat(12)tick();
  if(fault||check_enable||check_address!=0||!stop && run_enable)$fatal(1,"TAG165 normal STOP");
 endtask
 // Test-only queued STOP uses exactly the fields captured by a valid SPI
 // STOP. Allows cancellation at each reader edge (a full SPI frame is much
 // longer than this read). The normal test above sends the actual frame.
 task queued_stop;
  dut.pending=1;refdut.pending=1;dut.pending_command=4;refdut.pending_command=4;
  dut.pending_header_error=0;refdut.pending_header_error=0;dut.pending_causes=0;refdut.pending_causes=0;
  dut.pending_counter_clear=1;refdut.pending_counter_clear=1;
  dut.pending_counter_inc=0;refdut.pending_counter_inc=0;
 endtask
 initial begin
  normal(0);normal(19'hff);normal(19'hffff);normal(19'h1ffff);normal(19'h3ffff);normal(19'h40000);normal(19'h5ffff);
  for(integer bitnum=0;bitnum<19;bitnum++)begin
   begin_check(19'h12345);bad_mask=19'b1<<bitnum;request();repeat(26)tick();
   if(!fault||error_code!=7||dut.check_busy||dut.verified||check_address!=19'h12345)$fatal(1,"TAG165 wrong response accepted");corruptions++;
  end
  for(integer kind=0;kind<3;kind++)for(integer phase=0;phase<24;phase++)begin
   begin_check(19'h3ffff);request();repeat(phase)tick();
   if(kind==0)queued_stop();else if(kind==1)inject_fault=1;else reset=1;
   repeat(28)tick();
   if(check_enable||dut.check_busy||dut.verified||!psram_oe||!psram_we)$fatal(1,"TAG165 cancellation");
   if(kind==0 && (fault||check_address!=0))$fatal(1,"TAG165 STOP cancellation");
   if(kind==1 && (!fault||error_code!=9))$fatal(1,"TAG165 hard fault cancellation");
   cancels++;
  end
  // Directly overlap STOP and live wrong-address response, then hard fault.
  // Both must suppress counter clear and retain the established precedence.
  for(integer hard=0;hard<2;hard++)begin
   begin_check(19'h12345);bad_mask=19'h100;request();wait(raw_response);tick();queued_stop();inject_fault=hard;
   repeat(4)tick();
   if(!fault||error_code!=(hard?9:7)||check_address!=19'h12345)$fatal(1,"TAG165 response STOP priority");overlaps++;
  end
  $display("PASS TAG165 edges=%0d reads=%0d acks=%0d corruptions=%0d cancels=%0d overlaps=%0d",edges,reads,acks,corruptions,cancels,overlaps);$finish;
 end
 initial begin #10000000;$fatal(1,"TAG165 watchdog");end
endmodule
