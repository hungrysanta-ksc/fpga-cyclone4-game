// D0 init, D1 write next/read previous 512B, D2 final read, D3 status, D4 capability.
// At most 4MiB; incomplete packets cannot finish or release RUN.
module gbc_load_duplex(input wire clk,reset,run,cmd_ready,input wire[7:0]cmd,input wire end_message,input wire[31:0]byte_count,
 input wire rx_valid,input wire[15:0]rx_data,input wire tx_take,
 output wire[15:0]tx_data,output wire mode,stream_ready,lock_bus,inhibit_run,
 output wire[7:0]status,output wire req_valid,req_write,output wire[22:0]req_addr,
 output wire[15:0]req_data,input wire req_ready,rsp_valid,input wire[15:0]rsp_data);
 reg end_pending=0;
 reg session=0,last_done=1,final_done=0,fault=0,transaction=0;
 reg writing=0,reading=0,engine_start=0,engine_reset=0;
 reg[13:0]blocks=0;reg[8:0]received=0;
 reg[22:0]wb=0,rb=0;
 wire primed,done,error,tx_valid;
 wire[13:0]previous=blocks-1'b1;
 assign lock_bus=session&&!run;
 assign inhibit_run=session&&(!final_done||!last_done||fault||error);
 assign mode=session&&!run&&(cmd==8'hd1||cmd==8'hd2);
 assign stream_ready=primed&&!fault&&!error;
 assign status=8'hc0|{6'b0,!last_done,(fault||error)};
 gbc_load_words words(clk,reset||engine_reset,engine_start,writing,reading,wb,rb,
  rx_valid&&transaction,rx_data,tx_take&&transaction,tx_valid,tx_data,
  primed,done,error,req_valid,req_write,req_ready,req_addr,req_data,rsp_valid,rsp_data);
 always @(posedge clk)begin
  engine_start<=0;engine_reset<=0;end_pending<=end_message;
  if(reset)begin end_pending<=0;session<=0;last_done<=1;final_done<=0;fault<=0;transaction<=0;
   writing<=0;reading<=0;engine_start<=0;engine_reset<=0;blocks<=0;received<=0;wb<=0;rb<=0;
  end else begin
   if(end_pending&&mode&&byte_count!=514)fault<=1;
   if(rx_valid&&mode&&received==256)fault<=1;
   if(transaction&&rx_valid)begin
    if(received==256)fault<=1;else received<=received+1'b1;
   end
   if(transaction&&!engine_start&&done&&received==256)begin
    last_done<=1;transaction<=0;
    if(writing)blocks<=blocks+1'b1;else final_done<=1;
   end
   if(cmd_ready)begin
    if(cmd==8'hd0)begin
     if(run||!last_done)fault<=1;
     else begin session<=1;blocks<=0;received<=0;final_done<=0;fault<=0;engine_reset<=1;end
    end
    if(cmd==8'hd1||cmd==8'hd2)begin
     if(run||!session||!last_done||fault||error||final_done||
        (cmd==8'hd1&&blocks==8192)||(cmd==8'hd2&&blocks==0))fault<=1;
     else begin
      writing<=cmd==8'hd1;reading<=blocks!=0;wb<={2'b0,blocks[12:0],8'b0};rb<={2'b0,previous[12:0],8'b0};
      last_done<=0;transaction<=1;received<=0;engine_start<=1;
     end
    end
   end
  end
 end
endmodule
