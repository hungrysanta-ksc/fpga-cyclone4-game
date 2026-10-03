// Fixed priority: capture, builder read, builder write, planner, converter.
// A selected write retains priority while the downstream bridge defers it.
// Client 2 can replace its completed write on ACK; client 4 drops valid.
module video_router(input wire clk,reset,input wire capture_reserve,
 input wire[4:0]valid,writing,input wire[114:0]addresses,input wire[79:0]values,
 output wire[4:0]accepted,responded,output wire[15:0]response,
 output reg req_valid,req_write,output reg[22:0]req_addr,output reg[15:0]req_data,
 input wire req_ready,rsp_valid,input wire[15:0]rsp_data);
 // Reserve only selection; raw valid still drives client rearming.
 reg[4:0]armed;reg[2:0]selected,owner;integer i,j;
 always @* begin
  req_valid=0;req_write=0;req_addr=0;req_data=0;selected=0;
  for(j=0;j<5;j=j+1)if(!req_valid&&valid[j]&&armed[j]&&(j==0||!capture_reserve))begin
   req_valid=1;req_write=writing[j];req_addr=addresses[j*23+:23];
   req_data=values[j*16+:16];selected=j;
  end
 end
 assign accepted=(req_valid&&req_ready&&!reset)?(5'b1<<selected):5'b0;
 assign responded=(rsp_valid&&!reset)?(5'b1<<owner):5'b0;
 assign response=rsp_data;
 always @(posedge clk)begin
  if(reset)begin armed<=5'b11111;owner<=0;end
  else begin
   for(i=0;i<5;i=i+1)if(!valid[i])armed[i]<=1;
   if(rsp_valid&&owner==2)armed[2]<=1;
   if(req_valid&&req_ready)begin
    owner<=selected;if(selected==2||selected==4)armed[selected]<=0;
   end
  end
 end
endmodule
