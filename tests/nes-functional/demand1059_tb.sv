module demand1059_tb;
 reg clk=0,rst=1,stop=0,pv=0,short_plan=0;
 reg [1:0] kind=0;
 reg [15:0] gen=7;
 reg [47:0] rows=0;
 always #5 clk=!clk;
 wire ready,req,response_valid,done,drained,fault,core_ready,core_resp;
 wire [21:0] addr;reg [21:0] addr_q;
 reg [1:0] wait_q=0;reg response=0;
 integer cycles=0,n=0;
 wire [4:0] index;
 wire [7:0] data,core_data;
 wire core_req=cycles%13==0 && wait_q==0 && !response;
 function automatic [7:0] val(input [21:0] a);return a[16:9]^a[11:4]^{a[3:0],a[3:0]};endfunction
 nes_source_tile192 #(.EXTERNAL_PLAN(1)) d(.clk(clk),.reset(rst),.stop(stop),.frame_owned(1'b1),
   .geometry_valid(1'b1),.cap_release(1'b0),.frame_generation(gen),.source_ready(1'b1),.source_is_rom(1'b1),.source_writing(1'b0),
   .captured_epoch(32'd8),.live_epoch(32'd8),.plan_valid(pv),.plan_ready(ready),.plan_short(short_plan),
   .plan_slot(10'd1),.plan_tag(14'h1ffe),.plan_generation(gen),.plan_kind(kind),.plan_rows(rows),
   .plan_mask(8'hff),.plan_alt_mask(8'd0),.plan_alt_tags(112'd0),.qualified_slot(cycles%3==1),.core_safe(1'b1),
   .core_request(core_req),.core_address(22'h1234),.core_ready(core_ready),.core_response(core_resp),.core_data(core_data),
   .mem_ready(wait_q==0 && !response),.mem_request(req),.mem_address(addr),.mem_response(response),
   .mem_response_address(addr_q),.mem_error(1'b0),.bg_word(val(addr_q^22'd8)),.mem_data(val(addr_q)),
   .out_valid(response_valid),.out_ready(1'b1),.out_index(index),.out_data(data),.done(done),.drained(drained),.fault(fault));
 always @(posedge clk)begin
  cycles<=cycles+1;response<=0;
  if(req && wait_q==0 && !response)begin addr_q<=addr;wait_q<=2;end
  if(wait_q!=0)begin wait_q<=wait_q-1;if(wait_q==1)response<=1;end
  if(core_resp && core_data!==val(22'h1234))$fatal(1,"core data");
  if(fault)$fatal(1,"source fault");
  if(response_valid)begin
   if(stop || index!=n || data!==(n>=16?8'd0:val(22'h21ffe0+(n%2)*8+n/2)))$fatal(1,"tile index=%0d value=%h",index,data);
   n++;
  end
 end
 task submit;begin do @(negedge clk);while(!ready);pv=1;@(negedge clk);pv=0;end endtask
 initial begin
  for(int i=0;i<16;i++)rows[3*i+:3]=i/2;
  repeat(5)@(negedge clk);rst=0;
  for(integer mode=0;mode<4;mode++)begin
   kind=mode/2;short_plan=mode%2;n=0;submit();wait(done);@(negedge clk);
   if(n!=(kind?32:16))$fatal(1,"length");
  end
  n=0;submit();wait(wait_q==2 && addr_q[21]);@(negedge clk);stop=1;
  repeat(4)@(negedge clk);wait(drained);if(n || d.arbiter.owner)$fatal(1,"STOP returned stale tile data");
  $display("PASS VRC4 BG/OBJ both planes, CPU priority and pending ROM STOP");$finish;
 end
 initial begin repeat(5000)@(posedge clk);$fatal(1,"timeout n=%d phase=%d ready=%b req=%b fault=%b",n,d.tile.state,ready,req,fault);end
endmodule
