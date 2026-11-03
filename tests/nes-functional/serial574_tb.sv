// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module serial574_tb;
 reg mem_clk=0,nes_clk=0,mem_on=1,nes_on=1,reset=0,local_reset=1;
 reg load_begin=0,load_valid=0,loaded=0,run_enable=0,loader_fault=0;
 reg [18:0] loaded_bytes=19'h60000;
 always #2976 if(mem_on)mem_clk=!mem_clk;
 initial begin if($test$plusargs("SHIFT"))#11000;forever #23281 if(nes_on)nes_clk=!nes_clk;end
 wire source_ready,source_is_rom,source_writing;wire [31:0] live_epoch;
 nes_source_epoch207 dut(.*);
 reg [31:0] serial_model=0;
 integer cases=0,rx_edges=0,first_edge,latest_edge;
 integer min_edges=999,max_edges=0;
 reg late_a=0,late_b=0;
 always @(posedge nes_clk or posedge dut.rx_reset)
  if(dut.rx_reset)begin late_a<=0;late_b<=0;end
  else begin late_a<=dut.data_nes[0];late_b<=late_a;end
 initial if($test$plusargs("SKEW"))force dut.data_nes[1]=late_b;
 always @(posedge nes_clk)rx_edges++;
 task stopped;
  #2;if(source_ready||source_is_rom||!source_writing)$fatal(1,"invalid published");
 endtask
 task fresh;
  reset=1;loaded=0;run_enable=0;local_reset=1;load_begin=0;load_valid=0;loader_fault=0;
  loaded_bytes=19'h60000;
  mem_on=1;nes_on=1;repeat(4)@(negedge mem_clk);reset=0;serial_model=0;
 endtask
 task begin_load;
  @(negedge mem_clk);load_begin=1;serial_model++;
  stopped();@(negedge mem_clk);load_begin=0;
 endtask
 task verify;
  reg last_request;
  wait(dut.complete);latest_edge=rx_edges-first_edge;
  last_request=dut.request;
  if(latest_edge<min_edges)min_edges=latest_edge;
  if(latest_edge>max_edges)max_edges=latest_edge;
  if(latest_edge>256)$fatal(1,"serial deadline %0d",latest_edge);
  if(dut.received!==(serial_model^(serial_model>>1)))$fatal(1,"mixed identity");
  @(negedge nes_clk);local_reset=0;
  wait(source_ready);#2;
  if(live_epoch!==(serial_model^(serial_model>>1)))$fatal(1,"public identity");
  repeat(12)@(negedge nes_clk);
  if(!source_ready||dut.request!==last_request||dut.ack==dut.request)$fatal(1,"extra bit or missing terminal hold");
  cases++;
 endtask
 initial begin
  #100;
  for(int bitnum=0;bitnum<32;bitnum++)begin
   fresh();dut.serial=(32'd1<<bitnum)-1;serial_model=(32'd1<<bitnum)-1;
   begin_load();loaded=1;run_enable=1;first_edge=rx_edges;
   verify();
  end
  // Interrupt every partial word with STOP, a new load, a write or a fault.
  for(int mode=0;mode<6;mode++)for(int at=0;at<32;at++)begin
   fresh();begin_load();loaded=1;run_enable=1;first_edge=rx_edges;
   wait(dut.bit_index==at&&dut.active);@(negedge nes_clk);nes_on=0;
   case(mode)
    0:run_enable=0;
    1:begin_load();
    2:load_valid=1;
    3:loader_fault=1;
    4:loaded_bytes=19'h5ffff;
    5:loaded=0;
   endcase
   stopped();repeat(5)@(negedge mem_clk);
   // After a short BEGIN the memory clock may already publish a NEW request.
   // The stopped destination must still hold its reset and old ACK at zero.
   if(dut.complete||dut.ack||!dut.rx_reset)$fatal(1,"stopped-domain stale receiver mode=%0d bit=%0d",mode,at);
   run_enable=1;load_valid=0;loader_fault=0;loaded_bytes=19'h60000;loaded=1;
   repeat(3)@(negedge mem_clk);nes_on=1;first_edge=rx_edges;
   verify();
  end
  fresh();begin_load();loaded=1;run_enable=1;
  wait(dut.bit_index==7);@(negedge mem_clk);mem_on=0;
  repeat(12)@(negedge nes_clk);
  if(dut.complete)$fatal(1,"completed without producer");
  run_enable=0;stopped();#100;mem_on=1;repeat(5)@(negedge mem_clk);
  run_enable=1;first_edge=rx_edges;verify();
  // Invalidate a previously PUBLIC identity without either domain clock.
  mem_on=0;nes_on=0;run_enable=0;stopped();#100;
  if(live_epoch!==0||dut.complete||dut.ack||dut.request)$fatal(1,"halted publication retained");
  mem_on=1;nes_on=1;local_reset=1;repeat(5)@(negedge mem_clk);
  run_enable=1;first_edge=rx_edges;verify();
  fresh();dut.serial=32'hffffffff;begin_load();loaded=1;run_enable=1;
  local_reset=0;repeat(300)@(negedge nes_clk);
  if(!dut.exhausted||source_ready||dut.complete)$fatal(1,"wrap accepted");
  $display("PASS574 transfer=%0d edges=%0d..%0d",cases,min_edges,max_edges);$finish;
 end
 initial begin #(64'd3000000000);$fatal(1,"serial timeout");end
endmodule
