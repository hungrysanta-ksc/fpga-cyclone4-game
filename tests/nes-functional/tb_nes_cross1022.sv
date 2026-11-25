// SPDX-License-Identifier: MIT
module tb_nes_cross1022;
 reg clk=0, reset=1, stop=0, start=0, seal=0, release_bank=0, sample=0, query=0, alternate=0;
 reg [15:0] gen=0;
 reg [17:0] address;
 reg [7:0] value;
 wire [2:0] sr, cap, qr, resp, hit;
 wire [7:0] data[0:2];
 for(genvar i=0;i<3;i++) begin
  nes_obj_cross1022 #(.POLICY(i)) dut(.clk(clk),.reset(reset),.stop(stop),.immutable(1'b1),
    .start(start),.seal(seal),.release_bank(release_bank),.capture_gen(gen),.release_gen(gen),
    .sample(sample),.sample_address(address),.sample_data(value),.alternate(alternate),.query(query),
    .query_gen(gen),.query_address(address),.start_ready(sr[i]),.sample_ready(cap[i]),.query_ready(qr[i]),
    .response(resp[i]),.hit(hit[i]),.data(data[i]));
 end
 reg req=0;
 wire [1:0] valid_out, err_out, miss_req, port_ready;
 wire [7:0] byte_out[0:1];
 reg [1:0] backing=0;
 always @(posedge clk) backing<=miss_req;
 for(genvar j=0;j<2;j++) begin
  nes_probe_order1022 #(.REMEMBER(j)) port(.clk(clk),.reset(reset),.stop(stop),.immutable(1'b1),
   .start(start),.seal(seal),.release_bank(release_bank),.capture_gen(gen),.release_gen(gen),
   .sample(sample),.sample_address(address),.sample_data(value),.start_ready(),.sample_ready(),
   .request(req),.request_obj(1'b1),.address({4'h8,address}),.generation(gen),.ready(port_ready[j]),
   .idle(),.response(valid_out[j]),.error(err_out[j]),.data(byte_out[j]),.response_address(),.response_generation(),
   .back_request(miss_req[j]),.back_abort(),.back_address(),.back_generation(),.back_ready(1'b1),.back_idle(1'b1),
   .back_response(backing[j]),.back_error(1'b0),.back_response_address({4'h8,address}),
   .back_response_generation(gen),.back_data(value));
 end
 integer cycles[0:1], rom[0:1],elapsed;
 reg [1:0] seen;
 task tick; begin #5; clk=1; #5; clk=0; end endtask
 integer file, readings, demands, a,v,frames=0;
 integer p[0:2], m[0:2], miss[0:2];
 reg [2:0] primary_hit;
 initial begin
  file=$fopen("vectors.txt","r"); if(!file) $fatal;
  tick(); reset=0;
  while($fscanf(file,"%d %d",readings,demands)==2) begin
   repeat(270) tick(); gen=gen+1; #1; if(sr!==3'b111) $fatal;
   start=1; tick(); start=0;
   repeat(readings) begin
    if($fscanf(file,"%h %h",a,v)!=2) $fatal;
    address=a;value=v;sample=1; #1; if(cap!==3'b111) $fatal;
    tick();sample=0; repeat(2) tick();
   end
   seal=1; tick(); seal=0;
   for(int i=0;i<3;i++) begin p[i]=0;m[i]=0;miss[i]=0; end
   for(int i=0;i<2;i++) begin cycles[i]=0;rom[i]=0;end
   repeat(demands) begin
    if($fscanf(file,"%h %h",a,v)!=2) $fatal;
    query=1;address=a;alternate=0;tick(); if(resp!==3'b111 || (^hit)===1'bx) $fatal;
    primary_hit=hit;
    for(int i=0;i<3;i++) if(hit[i] && data[i]!==v[7:0]) $fatal;
    alternate=1;tick(); if(resp!==3'b111 || (^hit)===1'bx) $fatal;
    for(int i=0;i<3;i++) begin
     if(hit[i] && data[i]!==v[7:0]) $fatal;
     if(primary_hit[i]) p[i]++; else if(hit[i]) m[i]++; else miss[i]++;
    end
    query=0;
    value=v;req=1; #1; if(port_ready!==2'b11) $fatal; tick();req=0;seen=0;elapsed=1;
    while(seen!=3) begin
     for(int j=0;j<2;j++) begin
      if(valid_out[j]) begin
       if(seen[j] || byte_out[j]!==value || err_out[j]!==0) $fatal;
       cycles[j]+=elapsed;seen[j]=1;
      end
      if(miss_req[j]) rom[j]++;
     end
     tick();elapsed++;if(elapsed>12) $fatal;
    end
   end
   if(rom[0]!=rom[1] || rom[0]!=miss[0]) $fatal;
   $display("PORT1022 %0d %0d %0d %0d",frames,cycles[0],cycles[1],rom[0]);
   $display("OBJ1022 %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",frames,p[0],m[0],miss[0],p[1],m[1],miss[1],p[2],m[2],miss[2]);
   if(frames%2==0) begin
    stop=1; #1; if(hit!==0 || resp!==0) $fatal;
    tick(); stop=0;repeat(3) tick();
   end else begin release_bank=1;tick();release_bank=0;end
   query=1;tick(); if(hit!==0) $fatal;query=0;
   frames++;
  end
  if(frames!=120) $fatal;
  $display("PASS1022 120 sealed captures, checked bytes and cancel/release");$finish;
 end
endmodule
