`timescale 1ns/1ps
module lane140 #(parameter EARLY=0,parameter real RD=0,AD=0)(input clk,mem_clk,reset,input [24:0] ca,input [21:0] pa,input cr,cs,ce,pr,ps,pe,output fault,output[3:0] error,output[63:0] event_context);
 wire ready,request,response,cv,pv,trigger;wire[21:0] addr,ra,pins;wire[7:0] data,cd,pd;wire c1,c2,oe,we,bh,bl;
 nes_rom_early svc(.clk(clk),.reset(reset),.cpu_address_valid(ce),.ppu_address_valid(pe),.cpumem_addr(ca),.cpumem_read(cr),.cpu_sample(cs),.ppumem_addr(pa),.ppumem_read(pr),.ppu_sample(ps),.cpu_data(cd),.ppu_data(pd),.cpu_valid(cv),.ppu_valid(pv),.rom_ready(ready),.rom_request(request),.rom_address(addr),.rom_response(response),.rom_error(1'b0),.rom_response_address(ra),.rom_data(data),.fault_trigger(trigger),.fault_context(event_context),.fault(fault),.error_code(error));
 nes_rom_physical #(.EARLY_ACK(EARLY),.REQ_DELAY(RD),.ACK_DELAY(AD)) reader(.clk(clk),.mem_clk(mem_clk),.reset(reset),.check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),.rom_request(request),.rom_address(addr),.rom_ready(ready),.rom_response(response),.rom_error(),.rom_response_address(ra),.rom_data(data),.psram_address(pins),.psram_1ce(c1),.psram_2ce(c2),.psram_oe(oe),.psram_we(we),.psram_bhe(bh),.psram_ble(bl),.psram_data(16'h5aa5));
 always @(posedge clk) if(!reset && trigger)$display("FAIL140 early=%0d rd=%0f ad=%0f event_context=%h t=%0f",EARLY,RD,AD,event_context,$realtime);
endmodule
module unit140_tb;
 reg clk=0,mem_clk=0,reset=1;always #23.28 clk=~clk;
 real phase=0;initial begin void'($value$plusargs("PHASE=%f",phase));#(phase);forever #2.976 mem_clk=~mem_clk;end
 reg[24:0] ca=25'he183;reg[21:0] pa=22'h3a04ff;reg cr=0,cs=0,ce=1,pr=0,ps=0,pe=0;
 wire[4:0] fault;wire[3:0] error[0:4];wire[63:0] ctx[0:4];
 lane140 #(.EARLY(0),.RD(0),.AD(0)) ideal(clk,mem_clk,reset,ca,pa,cr,cs,ce,pr,ps,pe,fault[0],error[0],ctx[0]);
 lane140 #(.EARLY(0),.RD(3.722),.AD(4.693)) oldroute(clk,mem_clk,reset,ca,pa,cr,cs,ce,pr,ps,pe,fault[1],error[1],ctx[1]);
 lane140 #(.EARLY(1),.RD(3.722),.AD(4.693)) earlyroute(clk,mem_clk,reset,ca,pa,cr,cs,ce,pr,ps,pe,fault[2],error[2],ctx[2]);
 lane140 #(.EARLY(1),.RD(5.0),.AD(8.0)) margin(clk,mem_clk,reset,ca,pa,cr,cs,ce,pr,ps,pe,fault[3],error[3],ctx[3]);
 lane140 #(.EARLY(0),.RD(5.0),.AD(8.0)) oldmargin(clk,mem_clk,reset,ca,pa,cr,cs,ce,pr,ps,pe,fault[4],error[4],ctx[4]);
 task edgewait;@(posedge clk);#1;@(negedge clk);endtask
 initial begin
 repeat(5)edgewait();reset=0;repeat(20)edgewait();
 // Real139 trace: prior CPU byte cached, PPU early read one edge before new CPU address.
 pa=22'h201ff2;pe=1;edgewait();ca=25'he184;
 for(integer div=1;div<=12;div++)begin
  if(div==4)begin pe=0;pr=1;end
  if(div==6)cr=1;
  if(div==7)ps=1;
  if(div==8)begin ps=0;pr=0;pe=1;pa=22'h201ffa;end
  if(div==10)cs=1;
  if(div==11)begin cs=0;cr=0;end
  if(div==12)begin cs=1;pe=0;pr=1;end
  edgewait();
 end
 $display("RESULT140 phase=%0f faults=%b errors=%d/%d/%d/%d/%d",phase,fault,error[0],error[1],error[2],error[3],error[4]);$finish;
 end
endmodule
