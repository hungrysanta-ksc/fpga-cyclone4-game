// Fair two-client arbiter for the word-wide PSRAM background port.
// The downstream port allows one outstanding transaction. A response is
// routed with the owner captured when that transaction was admitted.
module psram_bg_arbiter(
 input wire clk,input wire reset,
 input wire capture_valid,input wire capture_write,input wire[22:0]capture_addr,
 input wire[15:0]capture_wdata,output wire capture_ready,
 output wire capture_rsp_valid,output wire[15:0]capture_rsp_data,
 input wire audio_valid,input wire audio_write,input wire[22:0]audio_addr,
 input wire[15:0]audio_wdata,output wire audio_ready,
 output wire audio_rsp_valid,output wire[15:0]audio_rsp_data,
 output wire bg_valid,output wire bg_write,output wire[22:0]bg_addr,
 output wire[15:0]bg_wdata,input wire bg_ready,
 input wire bg_rsp_valid,input wire[15:0]bg_rsp_data
);
 reg prefer_audio;
 reg owner_audio;
 wire select_audio=audio_valid&&(!capture_valid||prefer_audio);
 wire select_capture=capture_valid&&(!audio_valid||!prefer_audio);
 wire accepted=bg_ready&&(select_audio||select_capture);
 assign bg_valid=select_audio||select_capture;
 assign bg_write=select_audio?audio_write:capture_write;
 assign bg_addr=select_audio?audio_addr:capture_addr;
 assign bg_wdata=select_audio?audio_wdata:capture_wdata;
 assign capture_ready=bg_ready&&select_capture;
 assign audio_ready=bg_ready&&select_audio;
 assign capture_rsp_valid=bg_rsp_valid&&!owner_audio;
 assign audio_rsp_valid=bg_rsp_valid&&owner_audio;
 assign capture_rsp_data=bg_rsp_data;
 assign audio_rsp_data=bg_rsp_data;
 always @(posedge clk)begin
  if(reset)begin prefer_audio<=1'b0;owner_audio<=1'b0;end
  else if(accepted)begin
   owner_audio<=select_audio;
   // The client not just admitted wins the next simultaneous request.
   prefer_audio<=select_capture;
  end
 end
endmodule
