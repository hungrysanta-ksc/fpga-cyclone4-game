// Fixed FF3 geometry. Exercise every accepted byte and the final carry.
`timescale 1ns/1ps
module ff3_load_count_tb;
 logic clk=0,reset=1,go=0,valid=0,last=0,start=0,stop=0;
 always #5 clk=!clk;
 wire ready,loaded,run_enable,fault;
 wire [19:0] count;
 nes_rom_loader #(.SETUP_CYCLES(2),.WRITE_CYCLES(2),.HOLD_CYCLES(2),.RELEASE_CYCLES(2))
 loader(.mem_clk(clk),.reset(reset),.load_begin(go),.load_chr32(1'b0),.load_valid(valid),
        .load_data(8'hac),.commands_blocked(1'b0),.load_end(last),.start(start),.stop(stop),
        .load_ready(ready),.loaded(loaded),.run_enable(run_enable),.fault(fault),.loaded_bytes(count));
 initial begin
  repeat(6)@(negedge clk);reset=0;repeat(6)@(negedge clk);
  go=1;@(negedge clk);go=0;
  for(int i=0;i<524288;i++)begin
   while(!ready)@(negedge clk);
   if(count!==i || fault)$fatal(1,"before byte %0d count %h fault %b",i,count,fault);
   valid=1;@(negedge clk);valid=0;
  end
  wait(count==524288);@(negedge clk);last=1;@(negedge clk);last=0;
  wait(loaded);@(negedge clk);start=1;@(negedge clk);start=0;
  wait(run_enable);@(negedge clk);stop=1;@(negedge clk);stop=0;
  repeat(8)@(negedge clk);if(fault || run_enable || !loaded || count!=524288)$fatal(1,"STOP retained count");
  $display("PASS FF3 loader 524288 accepted bytes, START and retained STOP length");$finish;
 end
 initial begin #150ms;$fatal(1,"timeout count=%d phase=%h error=%h",count,loader.phase,loader.error_code);end
endmodule
