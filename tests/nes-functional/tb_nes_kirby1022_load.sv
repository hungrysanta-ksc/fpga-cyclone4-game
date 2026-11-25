// SPDX-License-Identifier: MIT
module tb_nes_kirby1022_load;
 reg clk=0, reset=1, begin_load=0, valid=0, finish_load=0, start=0, stop=0;
 reg checking=0, check=0;
 reg [19:0] offset;
 reg [7:0] value;
 wire ready, loaded, run, fault, check_ready, reply, check_fault;
 wire [19:0] count,reply_offset;
 wire [7:0] result;
 wire [21:0] pins;
 wire ce1,ce2,oe,we,bhe,ble;
 wire [15:0] bus;
 reg [7:0] source[0:786431], memory[0:4194303];
 reg request=0;
 reg [21:0] address;
 wire runtime_ready,runtime_reply,runtime_error;
 wire [21:0] returned;
 wire [7:0] runtime_data;
 wire [21:0] word_base={pins[19:0],ce1,1'b0};
 assign bus=(!oe && (ce1!=ce2))?{memory[word_base],memory[word_base+1]}:16'hzzzz;
 nes_rom_boot dut(.clk(clk),.mem_clk(clk),.reset(reset),.read_reset(1'b0),.check_enable(checking),
  .check_request(check),.check_address(offset),.check_ready(check_ready),.check_response(reply),
  .check_response_address(reply_offset),.check_data(result),.check_fault(check_fault),
  .load_begin(begin_load),.load_chr32(1'b0),.load_valid(valid),.load_end(finish_load),.start(start),.stop(stop),
  .load_data(value),.load_ready(ready),.loaded(loaded),.run_enable(run),.boot_fault(fault),.boot_error(),
  .loaded_bytes(count),.rom_chr32(),.rom_request(request),.rom_address(address),.rom_ready(runtime_ready),
  .rom_response(runtime_reply),.rom_error(runtime_error),.rom_response_address(returned),.rom_data(runtime_data),
  .bg_word(),.psram_address(pins),.psram_1ce(ce1),.psram_2ce(ce2),.psram_oe(oe),.psram_we(we),
  .psram_bhe(bhe),.psram_ble(ble),.psram_data(bus));
 // Shortened strobes for exhaustive functional replay; no timing claim.
 defparam dut.loader.SETUP_CYCLES=2,dut.loader.WRITE_CYCLES=2,dut.loader.HOLD_CYCLES=2,dut.loader.RELEASE_CYCLES=2;
 integer writes=0,fd;
 reg [21:0] physical;
 reg last_we=1;
 always @(posedge clk) last_we<=we;
 always @(posedge clk) if(last_we && !we) begin
  physical=writes<524288?writes:22'h200000+((writes-524288)&22'h3fff0)+((writes&7)<<1)+((writes>>3)&1);
  if({word_base[21:1],bhe}!==physical || bhe==ble || ce1==ce2 || oe!==1) $fatal;
  if((bhe?bus[7:0]:bus[15:8])!==source[writes]) $fatal;
  memory[physical]=source[writes];writes++;
 end
 task tick; begin #5;clk=1;#5;clk=0; end endtask
 initial begin
  fd=$fopen("payload.bin","rb");if(!fd || $fread(source,fd)!=786432) $fatal;$fclose(fd);
  tick();reset=0;repeat(6) tick();
  begin_load=1;tick();begin_load=0;
  for(int i=0;i<786432;i++) begin
   if(ready!==1 || count!==i) $fatal(1,"load %0d count=%0d",i,count);
   value=source[i];valid=1;tick();valid=0;repeat(8) tick();
  end
  if(count!==786432 || writes!=786432 || fault!==0) $fatal;
  finish_load=1;tick();finish_load=0;if(loaded!==1) $fatal;
  checking=1;repeat(8) tick();
  for(int i=0;i<786432;i++) begin
   if(check_ready!==1) $fatal(1,"check ready %0d",i);
   offset=i;check=1;tick();check=0;
   while(!reply) tick();
   if(reply_offset!==i || result!==source[i] || check_fault) $fatal(1,"readback %0d",i);
   tick();
  end
  checking=0;repeat(8) tick();start=1;tick();start=0;repeat(12) tick();
  if(run!==1) $fatal;
  // Check the first/last byte of every 1 KiB aperture through the RUN port.
  for(int i=0;i<786432;i++) if(i%1024==0 || i%1024==1023) begin
   address=i<524288?i:22'h200000+i-524288;
   while(!runtime_ready) tick();request=1;tick();request=0;
   while(!runtime_reply) tick();
   if(returned!==address || runtime_data!==source[i] || runtime_error) $fatal(1,"run %0d",i);
   tick();
  end
  stop=1;tick();stop=0;tick();if(run || !loaded) $fatal;
  stop=1;tick();stop=0;repeat(6) tick();
  if(run || count || fault || check_fault) $fatal;
  $display("PASS1022 786432 writes, 786432 independent CHECKs, 1536 RUN reads, STOP");$finish;
 end
 initial begin #800000000;$fatal(1,"timeout writes=%0d count=%0d",writes,count);end
endmodule
