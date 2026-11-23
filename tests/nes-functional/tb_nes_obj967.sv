// Isolate the first ROM wait on the shipped 964 reader and passive 905 recorder.
`timescale 1ns/1ps
module tb_nes_obj967;
 tb_nes_port914 #(.WINDOW957(1),.G(16'd909)) b();
 integer phase, tick=0, first_req=-1, first_grant=-1, previous=0, target=0;
 integer foreground=0, hint_rows=0, auxiliary=0;
 integer resume_tick, last_slot, issued_at;
 bit counting=0, active_tile=0, first_e9=0;
 string mode;
 nes_supply905 recorder(.clk(b.host),.reset(b.reset),.active(1'b1),.first_e9(first_e9),
  .nes_events(b.source.evt905),.writer(1'b0),.reader(1'b0),.returned(1'b0),.kind(1'b1),
  .units(8'd2),.token(32'd1),.generation(b.G),.query(1'b0),.set_page(1'b0),
  .page_in(8'd0),.index(5'd0),.reply());
 always @(negedge b.clk) if(counting)begin
  tick++;
  b.qualified=(tick<=last_slot || tick>=resume_tick) && tick%32==0;
 end
 always @(posedge b.clk) if(counting && !b.done_count)begin
  if(active_tile && b.source.shared_req && first_req<0)first_req=tick;
  if(b.source.shared_req && b.source.shared_ready)begin
   if(!b.qualified || b.core_req)$fatal(1,"unqualified ROM grant");
   if(active_tile)begin
    if(first_grant<0)first_grant=tick;
    target++;
    if(b.source.ahead.foreground)foreground++;
    else if(b.source.ahead.spec)hint_rows++;
    else if(b.source.ahead.aux952)auxiliary++;
    else $fatal(1,"ROM grant has no owner");
   end else previous++;
  end
 end
 task automatic send_page(input logic [55:0] packet);
  b.trace_run.ss964=0;#190;
  for(int i=55;i>=0;i--)begin
   b.trace_run.mosi964=packet[i];#95;b.trace_run.sck964=1;#190;b.trace_run.sck964=0;#95;
  end
  b.trace_run.ss964=1;
 endtask
 initial begin
  if(!$value$plusargs("phase=%d",phase)||!$value$plusargs("mode=%s",mode))$fatal;
  if(!(phase inside {1,2})||!(mode inside {"control","early","eight","late","other"}))$fatal;
  last_slot=phase==1?7000:6880;
  resume_tick=7500+(phase==1?200800:204990);
  #2;b.reset=1;repeat(10)@(negedge b.clk);b.reset=0;
  wait(b.cap_ready);@(negedge b.clk);b.cap_start=1;@(negedge b.clk);b.cap_start=0;
  repeat(8)@(negedge b.clk);b.cap_seal=1;@(negedge b.clk);b.cap_seal=0;
  repeat(280)@(negedge b.clk);counting=1;
  if(mode!="control")begin
   // Eight remaining 32-clock grant slots after the complete seven-byte SPI command.
   if(mode=="eight")wait(tick==(last_slot/32)*32-7*32-482);
   else wait(tick==(mode=="late"?6900:300));
   send_page(mode=="other"?56'heb8d0320015fa5:56'heb8d0318010ea5);
   wait(b.trace_run.page_valid);
   if(!b.source.page963 || b.source.page_base963*8!=(mode=="other"?'h120:'h118))$fatal(1,"wrong page identity");
  end
  wait(tick==7500);@(negedge b.host);active_tile=1;first_e9=1;issued_at=tick;
  @(negedge b.host);first_e9=0;
  b.count=1;b.size=0;b.crc='1;
  b.send_byte(8'h81);b.send_byte(b.G[7:0]);b.send_byte(b.G[15:8]);b.send_byte(8);
  b.send_byte(0);b.send_byte(8'h18);b.send_byte(1);b.send_byte(255);
  @(negedge b.host);b.write_en=0;b.seal=1;@(negedge b.host);b.seal=0;
  wait(b.done_count==1);
  begin
   integer finished;
   finished=tick;
   repeat(8)@(negedge b.host);
   if(b.bytes_out!=32 || b.fault || b.batch_fault || recorder.tiles!=1 ||
      recorder.tile_log[0][35:30]!==target[5:0] || target>63)$fatal(1,"output or trace mismatch");
   if(mode=="early" || mode=="eight")begin
    if(previous!=(mode=="eight"?8:128) || target!=0 || finished>=resume_tick)
     $fatal(1,"resident row missed: pre=%0d target=%0d finished=%0d",previous,target,finished);
   end else begin
    if(target<8 || finished<resume_tick || first_req>=resume_tick || first_grant<resume_tick)
     $fatal(1,"expected a closed ROM window");
    if(previous!=(mode=="other"?128:0))$fatal(1,"wrong pre-plan traffic");
   end
   $display("PASS967 mode=%s phase=%0d E9=%0d done=%0d before=%0d observed=%0d demand=%0d hint=%0d aux=%0d first_req=%0d first_grant=%0d",
     mode,phase,issued_at,finished,previous,target,foreground,hint_rows,auxiliary,first_req,first_grant);
  end
  $finish;
 end
 initial begin #15000000;$fatal(1,"timeout tick=%0d",tick);end
endmodule
