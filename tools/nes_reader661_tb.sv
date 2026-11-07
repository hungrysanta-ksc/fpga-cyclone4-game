`timescale 1ns/1ps
// Compare pins and replies on every half edge. Data and the extra lane are
// compared only once their respective sampling flops have defined values.
module reader661_case #(parameter N=16, parameter SEED=1)(output reg done=0);
 reg clk=0, mem=0, reset=0, cm=0, cq=0, rq=0, valid_addr=1, blocked=0;
 reg [21:0] ca=0, ra=0;
 reg [15:0] dq=0;
 always #23.281 clk=~clk;
 always #2.976 mem=~mem;
 wire [2:0] cr,cp,rr,rp,err;
 wire [21:0] caddr[3],raddr[3],pins[3];
 wire [7:0] cd[3],rd[3],bg[3]; wire [5:0] ctl[3];
 `define PORTS(I,Q) .clk(clk),.mem_clk(mem),.reset(reset),.check_mode(cm),.check_request(Q),.check_address(ca), \
 .check_ready(cr[I]),.check_response(cp[I]),.check_response_address(caddr[I]),.check_data(cd[I]), \
 .rom_request(rq),.rom_address(ra),.rom_ready(rr[I]),.rom_response(rp[I]),.rom_error(err[I]), \
 .rom_response_address(raddr[I]),.rom_data(rd[I]),.bg_word(bg[I]),.psram_address(pins[I]), \
 .psram_1ce(ctl[I][5]),.psram_2ce(ctl[I][4]),.psram_oe(ctl[I][3]),.psram_we(ctl[I][2]), \
 .psram_bhe(ctl[I][1]),.psram_ble(ctl[I][0]),.psram_data(dq)
 baseline #(.READ_CYCLES(N),.HOLD_SOURCE_IN_CHECK(1)) r0(`PORTS(0,cq && cr[0] && valid_addr && !blocked));
 counter_reader #(.READ_CYCLES(N),.HOLD_SOURCE_IN_CHECK(1)) r1(`PORTS(1,cq && valid_addr && !blocked));
 pipe_reader #(.READ_CYCLES(N),.HOLD_SOURCE_IN_CHECK(1)) r2(`PORTS(2,cq && valid_addr && !blocked));
 `undef PORTS
 integer hits=0,checks=0,seed=SEED,i,epoch;
 always @(negedge mem)begin
  for(integer j=1;j<=2;j++)
   if({cr[0],cp[0],rr[0],rp[0],err[0],caddr[0],raddr[0],pins[0],ctl[0],rd[0],cd[0],bg[0]} !==
      {cr[j],cp[j],rr[j],rp[j],err[j],caddr[j],raddr[j],pins[j],ctl[j],rd[j],cd[j],bg[j]})
    $fatal(1,"reader mismatch N=%d epoch=%d cycle=%d candidate=%d",N,epoch,i,j);
  if(cp[0])checks++;
 end
 always @(negedge clk)if(rp[0])hits++;
 initial begin
  #1;reset=1;
  for(epoch=0;epoch<48;epoch++)begin
   cm=epoch[0];
   repeat(24)@(negedge mem);
   #1;reset=0;
   for(i=0;i<110+epoch;i++)begin
    @(negedge mem);#0.2;
    {rq,cq,valid_addr,blocked}= $random(seed);
    dq=$random(seed);ca=$random(seed);ra=$random(seed);
   end
   #0.7;reset=1;#0.1;
   if(!(&ctl[0][5:3]) || !(&ctl[1][5:3]) || !(&ctl[2][5:3]))
    $fatal(1,"pin release on async reset");
  end
  if(hits<20 || checks<20)$fatal(1,"insufficient completions");
  $display("PASS661 READ_CYCLES=%0d RUN=%0d CHECK=%0d",N,hits,checks);done=1;
 end
endmodule
module reader661_tb;
 wire a,b,c;
 reader661_case #(1,17) one(a); reader661_case #(3,53) three(b); reader661_case #(16,91) board(c);
 initial begin wait(a&&b&&c);$finish;end
endmodule
