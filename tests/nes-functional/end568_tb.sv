// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module end568_tb;
 reg mem_clk=0,reset=0,load_begin=0,load_chr32=0,load_valid=0,load_end=0,start=0,stop=0,commands_blocked=0;
 reg [7:0] load_data=0;
 always #3 mem_clk=!mem_clk;
 `define PORTS .mem_clk(mem_clk),.reset(reset),.load_begin(load_begin),.load_chr32(load_chr32),.load_valid(load_valid),.load_end(load_end),.start(start),.stop(stop),.load_data(load_data),.commands_blocked(commands_blocked)
 nes_rom_loader dut(`PORTS);
 loader567 refdut(`PORTS);
 `undef PORTS
 `define VIEW(m) {m.phase,m.terminal,m.remaining,m.count_complete,m.fault,m.error_code,m.loaded_bytes,m.loaded,m.check_loaded,m.rom_chr32,m.run_enable,m.load_ready,m.load_address,m.load_pin_data,m.load_drive,m.load_1ce,m.load_2ce,m.load_oe,m.load_we,m.load_bhe,m.load_ble}
 task check;
  if(`VIEW(dut)!==`VIEW(refdut)||{dut.illegal_begin,dut.illegal_start,dut.illegal_end,dut.illegal_data}!==
     {refdut.illegal_begin,refdut.illegal_start,refdut.illegal_end,refdut.illegal_data}||dut.local_fault!==refdut.local_fault)
   $fatal(1,"loader divergence phase=%h END=%d CHECK_failed=%d",refdut.phase,load_end,commands_blocked);
 endtask
 integer cases=0,phase_mask;
 initial begin
  #1;reset=1;repeat(2)@(negedge mem_clk);reset=0;repeat(4)@(negedge mem_clk);
  for(int st=0;st<17;st++)for(int c=0;c<32;c++)for(int flags=0;flags<16;flags++)begin
   @(negedge mem_clk);
   phase_mask=(st==16)?0:(1<<st);
   dut.phase=phase_mask;refdut.phase=phase_mask;
   refdut.reject_state={st==0||st==4||st==5,st==0||st==4||st==5||st==2||st==3||st==7||st==8,
      st==0||st==1||st==5||st==2||st==3||st==7||st==8,st==1||st==5||st==2||st==3||st==7||st==8};
`ifdef LATE568
   dut.reject_state=refdut.reject_state;
`elsif END_ONLY568
   dut.reject_state=refdut.reject_state[1:0];dut.reject_data_state=refdut.reject_state[3];
`endif
   {load_begin,load_valid,load_end,start,stop}=c;
   {commands_blocked,dut.fault,dut.count_complete,dut.terminal}=flags;
   refdut.fault=dut.fault;refdut.count_complete=dut.count_complete;refdut.terminal=dut.terminal;
   dut.remaining=dut.terminal?1:2;refdut.remaining=dut.remaining;
   dut.error_code=c%16;refdut.error_code=dut.error_code;
   #1;check();@(posedge mem_clk);#1;check();
   @(negedge mem_clk);commands_blocked=!commands_blocked;{load_begin,load_valid,load_end,start,stop}=31-c;
   #1;check();@(posedge mem_clk);#1;check();cases++;
  end
  $display("PASS568 loader=%0d",cases);$finish;
 end
endmodule
