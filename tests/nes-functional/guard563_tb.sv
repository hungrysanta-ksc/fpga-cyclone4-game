// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module guard563_tb;
 reg mem_clk=0,ref_clk=0,mem_on=1,ref_on=1,locked=0;
 always #2976 if(mem_on)mem_clk=!mem_clk;
 initial begin if($test$plusargs("SHIFT"))#3100;forever #23281 if(ref_on)ref_clk=!ref_clk;end
 wire guard_reset=!locked;
 wire guard_allow,guard_fault,release_memory,startup_ready,external_memory_ready,diagnostic_reset;
 nes_diag_clock_guard127 clock_guard(.mem_clk(mem_clk),.ref_clk(ref_clk),.reset(guard_reset),.allow_memory(guard_allow),.fault(guard_fault));
`ifdef SPLIT
 nes_clock_release563 memory_release(.clk(mem_clk),.kill(guard_reset||guard_fault),.qualified(guard_allow),.reset_out(release_memory));
`else
 nes_domain_reset124 memory_release(.clk(mem_clk),.raw_reset(guard_reset||!guard_allow),.reset(release_memory));
`endif
 nes_diag_startup_guard #(.WAIT_CYCLES(33603)) startup(.clk(mem_clk),.reset(release_memory),.ready(startup_ready));
 assign external_memory_ready=!release_memory && startup_ready;
 nes_domain_reset124 diagnostic_release(.clk(mem_clk),.raw_reset(!external_memory_ready),.reset(diagnostic_reset));
 reg request=0;reg [21:0] address;
 wire ready,reply,oe,we,c1,c2,bhe,ble,err;wire [21:0] pins,reply_addr;wire [7:0] data;
 wire [7:0] test_byte=pins[7:0]^{7'b0,c1};
 nes_rom_physical #(.READ_CYCLES(16),.HOLD_SOURCE_IN_CHECK(1)) reader(
   .clk(ref_clk),.mem_clk(mem_clk),.reset(diagnostic_reset),.check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),
   .rom_request(request),.rom_address(address),.rom_ready(ready),.rom_response(reply),.rom_error(err),
   .rom_response_address(reply_addr),.rom_data(data),.psram_address(pins),.psram_1ce(c1),.psram_2ce(c2),
   .psram_oe(oe),.psram_we(we),.psram_bhe(bhe),.psram_ble(ble),.psram_data({test_byte,~test_byte}));
 integer mem_edges=0,replies=0,mark,sampled;
 reg [21:0] held;
 always @(posedge mem_clk)begin
   mem_edges++;
   if(reader.mr)sampled=-1;
   else begin
    if(reader.request_toggle!=reader.request_sync[0])begin sampled=mem_edges;held=reader.address_hold;end
    if(reader.state==reader.IDLE && reader.pending && !reader.owner_check)begin
     if(sampled<0||mem_edges-sampled!=2||reader.address_hold!==held)$fatal(1,"RUN capture edge");
     $display("CAPTURE563 %0d %h %0t",mem_edges-sampled,held,$time);sampled=-1;
    end
   end
 end
 always @(posedge ref_clk)if(reply)begin replies++;$display("REPLY563 %h %0t",reply_addr,$time);end
 always @(negedge release_memory)if($time>100000)begin
   if(!guard_allow||guard_fault)$fatal(1,"unqualified release");
   mark=mem_edges;
 end
 always @(posedge external_memory_ready)begin
   if(!guard_allow||mem_edges-mark!=33604)$fatal(1,"startup window %0d",mem_edges-mark);
   $display("START563 %0t",$time);
 end
 task check_off;
   if(release_memory!==1'b1||external_memory_ready!==1'b0||diagnostic_reset!==1'b1||
      !oe||!c1||!c2||!we||ready||reply||err)$fatal(1,"shutdown");
 endtask
 task restart;
   locked=0;request=0;#1000;check_off();
   mem_on=1;ref_on=1;repeat(10)@(negedge ref_clk);locked=1;
 endtask
 task read_start(input [21:0] a);
   @(negedge ref_clk);while(!ready)@(negedge ref_clk);
   address=a;request=1;@(negedge ref_clk);request=0;
 endtask
 task good_read(input [21:0] a);
   reg [7:0] value;
   value=a[9:2]^{7'b0,a[1]};
   read_start(a);while(!reply)@(negedge ref_clk);
   if(reply_addr!==a||data!==(a[0]?~value:value))$fatal(1,"reply content");
   @(negedge ref_clk);if(reply)$fatal(1,"duplicate");
 endtask
 task loss(input bit stop_mem,input integer mode);
   time lost;
   integer old_count;
   restart();
   case(mode)
    0:repeat(2)@(negedge mem_clk); // Before both domains qualify
    1:begin wait(!release_memory);repeat(30)@(negedge mem_clk);end
    2:begin wait(!diagnostic_reset);good_read(22'h1234);
      read_start(22'h201237);wait(!oe);end
   endcase
   #1;lost=$time;old_count=replies;
   if(stop_mem)mem_on=0;else ref_on=0;
   wait(guard_fault);#1;check_off();
   if(replies!=old_count)$fatal(1,"canceled read escaped");
   $display("LOSS563 %0d %0d %0d",stop_mem,mode,$time-lost);
   if(stop_mem && $time-lost>3200000)$fatal(1,"reference watchdog late");
   if(!stop_mem && $time-lost>4100000)$fatal(1,"memory watchdog late");
   mem_on=1;ref_on=1;repeat(700)@(negedge mem_clk);check_off();
   if(!guard_fault||replies!=old_count)$fatal(1,"uncommanded rearm");
 endtask
 initial begin
   #200000;
   for(int mode=0;mode<=2;mode++)begin loss(1,mode);loss(0,mode);end
   restart();wait(!diagnostic_reset);good_read(22'h302);
   read_start(22'h105);wait(!oe);#1;mem_on=0;ref_on=0;locked=0;#1000;check_off();
   restart();wait(!diagnostic_reset);good_read(22'h581);
   $display("PASS563 6 losses and common reset");$finish;
 end
 initial begin #(64'd3000000000);$fatal(1,"timeout");end
endmodule
