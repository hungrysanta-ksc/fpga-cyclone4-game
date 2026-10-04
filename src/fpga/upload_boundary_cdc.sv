// SNES-side upload transaction. Software starts an upload and polls completion
// before reading the frame window. The bus adapter must block NEW frame reads
// while bus_busy is high; bus_read_idle confirms earlier reads have drained.
// Both clock domains require the same asynchronously asserted reset.
module upload_boundary_cdc(
 input wire bus_clk,source_clk,reset,upload_start,bus_read_idle,
 output wire bus_busy,output reg upload_done,bus_page,bus_front_valid,protocol_error,
 output wire source_boundary,source_read_idle,
 input wire source_page,source_front_valid
);
 (* async_reg = "true" *) reg[1:0]brst,srst,req_sync,ack_sync;
 reg request_toggle,response_toggle;
 reg held_page,held_valid;
 reg[1:0]bus_state,source_state;
 always @(posedge bus_clk or posedge reset)
  if(reset)brst<=3;else brst<={brst[0],1'b0};
 always @(posedge source_clk or posedge reset)
  if(reset)srst<=3;else srst<={srst[0],1'b0};
 always @(posedge bus_clk or posedge brst[1])
  if(brst[1])ack_sync<=0;else ack_sync<={ack_sync[0],response_toggle};
 always @(posedge source_clk or posedge srst[1])
  if(srst[1])req_sync<=0;else req_sync<={req_sync[0],request_toggle};
 assign bus_busy=brst[1]||bus_state!=0;
 assign source_boundary=source_state==1&&!srst[1]&&!reset;
 // A received request certifies that the bus is locked and earlier reads ended.
 assign source_read_idle=source_boundary;
 always @(posedge bus_clk or posedge brst[1])begin
  if(brst[1])begin bus_state<=0;request_toggle<=0;upload_done<=0;
   bus_page<=0;bus_front_valid<=0;protocol_error<=0;end
  else begin
   upload_done<=0;
   if(upload_start&&bus_state!=0)protocol_error<=1;
   case(bus_state)
    0:if(upload_start)bus_state<=1;
    1:if(bus_read_idle)begin request_toggle<=!request_toggle;bus_state<=2;end
    2:if(ack_sync[1]==request_toggle)begin
     bus_page<=held_page;bus_front_valid<=held_valid;upload_done<=1;bus_state<=0;
    end
   endcase
  end
 end
 always @(posedge source_clk or posedge srst[1])begin
  if(srst[1])begin source_state<=0;response_toggle<=0;held_page<=0;held_valid<=0;end
  else case(source_state)
   0:if(req_sync[1]!=response_toggle)source_state<=1;
   1:source_state<=2; // display_pages samples source_boundary at this edge.
   2:begin // Now capture the post-publication page; it stays stable until ACK.
    held_page<=source_page;held_valid<=source_front_valid;
    response_toggle<=req_sync[1];source_state<=0;
   end
  endcase
 end
endmodule
