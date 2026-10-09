// SPDX-License-Identifier: MIT
// One-step differential check of the actual130 and131 RTL at legal byte counts.
`timescale 1ns/1ps
module counter131_diff_tb;
 reg mem_clk=0,reset=1;
 always #2.976 mem_clk=~mem_clk;
 reg load_begin=0,load_chr32=0,load_valid=0,load_end=0,start=0,stop=0;
 reg [7:0] load_data=8'h5a;
 nes_rom_loader dut(.mem_clk(mem_clk),.reset(reset),.load_begin(load_begin),.load_chr32(load_chr32),.load_valid(load_valid),.load_end(load_end),.start(start),.stop(stop),.load_data(load_data));
 nes_rom_loader_reference refdut(.mem_clk(mem_clk),.reset(reset),.load_begin(load_begin),.load_chr32(load_chr32),.load_valid(load_valid),.load_end(load_end),.start(start),.stop(stop),.load_data(load_data));
 integer checks=0;
 initial begin
  repeat(4)@(negedge mem_clk);reset=0;repeat(4)@(negedge mem_clk);
  for(integer mode=0;mode<2;mode++)
   for(integer state=0;state<9;state++)
    for(integer commands=0;commands<64;commands++)
     for(integer length_case=0;length_case<3;length_case++)
      for(integer failed=0;failed<2;failed++)
       for(integer rem_case=0;rem_case<4;rem_case++)begin
        integer length,remaining;
        // FAILED is entered only with the sticky fault set; arbitrary state
        // register corruption is outside this reachable-state comparison.
        if(state==6 && !failed)continue;
        length=length_case==0?0:(mode?98304:81920)-(length_case==1?1:0);
        remaining=rem_case==0?1:rem_case==1?2:rem_case==2?22:64;
        @(negedge mem_clk);
        {load_begin,load_valid,load_end,start,stop,load_chr32}=commands;
        dut.state=state;refdut.state=state;dut.remaining=remaining;refdut.remaining=remaining;
        dut.chr32=mode;refdut.chr32=mode;dut.loaded_bytes=length;refdut.loaded_bytes=length;
        dut.fault=failed;refdut.fault=failed;dut.error_code=0;refdut.error_code=0;
        dut.chip=0;refdut.chip=0;dut.lane=1;refdut.lane=1;dut.byte_hold=8'ha5;refdut.byte_hold=8'ha5;
        dut.load_address=22'h124;refdut.load_address=22'h124;
        @(posedge mem_clk);#0.001;
        if({dut.state,dut.chr32,dut.loaded_bytes,dut.fault,dut.error_code,dut.chip,dut.lane,dut.byte_hold,dut.load_address} !==
           {refdut.state,refdut.chr32,refdut.loaded_bytes,refdut.fault,refdut.error_code,refdut.chip,refdut.lane,refdut.byte_hold,refdut.load_address})
         $fatal(1,"DIFF131 state=%0d commands=%0d length=%0d failed=%0d remaining=%0d",state,commands,length,failed,remaining);
        // Remaining is unobservable outside timed phases and reloaded before
        // accepting data. Every active next state must still match exactly.
        if((dut.state==2 || dut.state==3 || dut.state==7 || dut.state==8) && dut.remaining!==refdut.remaining)
         $fatal(1,"DIFF131 active counter state=%0d command=%0d",state,commands);
        if({dut.load_ready,dut.loaded,dut.run_enable,dut.load_pin_data,dut.load_drive,dut.load_1ce,dut.load_2ce,dut.load_oe,dut.load_we,dut.load_bhe,dut.load_ble} !==
           {refdut.load_ready,refdut.loaded,refdut.run_enable,refdut.load_pin_data,refdut.load_drive,refdut.load_1ce,refdut.load_2ce,refdut.load_oe,refdut.load_we,refdut.load_bhe,refdut.load_ble})
         $fatal(1,"DIFF131 observable pins");
        checks++;
       end
  $display("PASS131 DIFF one_step_cases=%0d counts_at_0_totalminus1_total=1",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"DIFF131 watchdog");end
endmodule
