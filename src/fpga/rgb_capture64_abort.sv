// Lossless RGB555 -> encounter-order frame-local IDs (black is always ID 0).
// External byte addresses: map 00000..0ffff, low ID bytes 10000..159ff, high-bit words 16000..16b3f,
// dictionary 1c000..1c3ff. Each transaction is 16 bits and must receive an
// acknowledgement (rsp_valid), including writes, after request acceptance.
// Source is not backpressured: FIFO overflow aborts the frame, never drops pixels.
module rgb_capture64_abort (
 input wire clk_sys, reset, start, abort_frame,
 output reg aborted,
 input wire pixel_valid,
 input wire [14:0] pixel_rgb,
 output wire capture_active,
 output wire req_valid, req_write,
 input wire req_ready,
 output wire [16:0] req_addr,
 output wire [15:0] req_data,
 input wire rsp_valid,
 input wire [15:0] rsp_data,
 output reg [9:0] color_count,
 output reg done, error,
 output reg [1:0] error_code,
 output wire busy,
 output wire [6:0] fifo_level,output wire[7:0] debug_state
);
 localparam IDLE=0, BOOT_REQ=1, BOOT_WAIT=2, CLEAR_REQ=3, CLEAR_WAIT=4,
 BLACK_REQ=5, BLACK_WAIT=6, DICT0_REQ=7, DICT0_WAIT=8,
 TAKE=9, LOOKUP=10, MAP_REQ=11, MAP_WAIT=12, NEW_REQ=13, NEW_WAIT=14,
 DICT_REQ=15, DICT_WAIT=16, PACK=17, WRITE_REQ=18, WRITE_WAIT=19, FAILED=20, HIGH_REQ=21, HIGH_WAIT=22;
 reg [4:0] state;
 reg initialized,active,abort_pending;
 reg [6:0] epoch;
 reg [14:0] sweep_start,clear_at;
 reg [8:0] clear_left;
 (* ramstyle="M9K" *) reg [14:0] fifo[0:63];
 reg [5:0] head,tail;
 reg [6:0] queued;
 reg [14:0] received,consumed;
 reg [14:0] rgb_q;
 reg [8:0] id_q;reg[7:0]low_id;reg[15:0]high_bits;
 (* ramstyle="logic" *) reg [14:0] cache_rgb[0:15];
 (* ramstyle="logic" *) reg [8:0] cache_id[0:15];
 reg [15:0] cache_valid;
 reg [3:0] victim;
 reg hit;
 reg [8:0] hit_id;
 integer k;
 wire pop=state==TAKE && queued!=0 && !abort_pending && !abort_frame;
 wire push=active && !abort_pending && !abort_frame && pixel_valid && received<23040 && (queued<64 || pop);
 assign capture_active=active;
 assign debug_state={initialized,abort_pending,1'b0,received==23040,queued!=0,3'b0};
 assign fifo_level=queued;
 assign busy=state!=IDLE && state!=FAILED;
 always @* begin
  hit=0;hit_id=0;
  for(k=0;k<16;k=k+1) if(cache_valid[k] && cache_rgb[k]==rgb_q) begin hit=1;hit_id=cache_id[k];end
 end
 assign req_valid=state==BOOT_REQ || state==CLEAR_REQ || state==BLACK_REQ || state==DICT0_REQ || state==MAP_REQ || state==NEW_REQ || state==DICT_REQ || state==WRITE_REQ || state==HIGH_REQ;
 assign req_write=state!=MAP_REQ;
 assign req_addr=(state==BOOT_REQ || state==CLEAR_REQ) ? {1'b0,clear_at,1'b0} :
                 state==BLACK_REQ ? 17'd0 : state==DICT0_REQ ? 17'h1c000 :
                 (state==MAP_REQ || state==NEW_REQ) ? {1'b0,rgb_q,1'b0} :
                 state==DICT_REQ ? (17'h1c000+{7'b0,id_q,1'b0}) :
                 state==HIGH_REQ ? (17'h16000+{5'b0,consumed[14:4],1'b0}) : (17'h10000+{2'b0,consumed[14:1],1'b0});
 assign req_data=(state==BOOT_REQ || state==CLEAR_REQ || state==DICT0_REQ) ? 16'd0 :
                 state==BLACK_REQ ? {epoch,9'd0} : state==NEW_REQ ? {epoch,id_q} :
                 state==DICT_REQ ? {1'b0,rgb_q} : state==HIGH_REQ ? high_bits : {id_q[7:0],low_id};
 always @(posedge clk_sys) begin if(push&&!reset)fifo[tail]<=pixel_rgb;if(pop&&!reset)rgb_q<=fifo[head];end
 always @(posedge clk_sys) begin
  if(reset) begin
   state<=IDLE;initialized<=0;abort_pending<=0;aborted<=0;active<=0;epoch<=1;sweep_start<=0;
   clear_at<=0;clear_left<=0;head<=0;tail<=0;queued<=0;received<=0;consumed<=0;
   id_q<=0;low_id<=0;high_bits<=0;cache_valid<=0;victim<=0;
   color_count<=1;done<=0;error<=0;error_code<=0;
  end else begin
   done<=0;aborted<=0;
   if(abort_frame&&active)abort_pending<=1;
   if(push) begin tail<=tail+1'b1;received<=received+1'b1;end
   if(pop) begin head<=head+1'b1;end
   case({push,pop})
    2'b10:queued<=queued+1'b1;
    2'b01:queued<=queued-1'b1;
    default:;
   endcase
   // Drain every accepted memory transaction before abandoning a partial
   // frame. Finish the scheduled epoch sweep even when cancellation arrives
   // during CLEAR, so repeated cancellations cannot resurrect old map tags.
   if(abort_pending && (state==TAKE||state==LOOKUP||state==PACK||state==IDLE))begin
    state<=IDLE;active<=0;abort_pending<=0;aborted<=1;
    head<=0;tail<=0;queued<=0;received<=0;consumed<=0;cache_valid<=0;
    epoch<=epoch==127 ? 7'd1 : epoch+1'b1;
   end else if(start && state==IDLE) begin
    // Warm starts may buffer pixels while the 259-entry sweep is finishing.
    // Cold boot still requires the caller to hold the GBC until armed.
    active<=initialized;
    error<=0;error_code<=0;head<=0;tail<=0;queued<=0;received<=0;consumed<=0;
    color_count<=1;cache_valid<=0;victim<=0;clear_left<=259;
    clear_at<=initialized ? sweep_start : 15'd0;
    state<=initialized ? CLEAR_REQ : BOOT_REQ;
   end else case(state)
    BOOT_REQ:if(req_ready)state<=BOOT_WAIT;
    BOOT_WAIT:if(rsp_valid) begin
     if(clear_at==32767)begin initialized<=1;clear_at<=sweep_start;state<=CLEAR_REQ;end
     else begin clear_at<=clear_at+1'b1;state<=BOOT_REQ;end
    end
    CLEAR_REQ:if(req_ready)state<=CLEAR_WAIT;
    CLEAR_WAIT:if(rsp_valid)begin
     if(clear_left==1 || clear_at==32767)begin
      sweep_start<=clear_at==32767 ? 15'd0 : clear_at+1'b1;state<=BLACK_REQ;
     end else begin clear_at<=clear_at+1'b1;clear_left<=clear_left-1'b1;state<=CLEAR_REQ;end
    end
    BLACK_REQ:if(req_ready)state<=BLACK_WAIT;
    BLACK_WAIT:if(rsp_valid)state<=DICT0_REQ;
    DICT0_REQ:if(req_ready)state<=DICT0_WAIT;
    DICT0_WAIT:if(rsp_valid)begin active<=1;state<=TAKE;end
    TAKE:if(pop)state<=LOOKUP;
    LOOKUP:if(hit)begin id_q<=hit_id;state<=PACK;end else state<=MAP_REQ;
    MAP_REQ:if(req_ready)state<=MAP_WAIT;
    MAP_WAIT:if(rsp_valid)begin
     if(rsp_data[15:9]==epoch)begin
      id_q<=rsp_data[8:0];cache_rgb[victim]<=rgb_q;cache_id[victim]<=rsp_data[8:0];cache_valid[victim]<=1;victim<=victim+1'b1;state<=PACK;
     end else if(color_count==512)begin error<=1;error_code<=2;active<=0;state<=FAILED;end
     else begin id_q<=color_count[8:0];color_count<=color_count+1'b1;state<=NEW_REQ;end
    end
    NEW_REQ:if(req_ready)state<=NEW_WAIT;
    NEW_WAIT:if(rsp_valid)state<=DICT_REQ;
    DICT_REQ:if(req_ready)state<=DICT_WAIT;
    DICT_WAIT:if(rsp_valid)begin
     cache_rgb[victim]<=rgb_q;cache_id[victim]<=id_q;cache_valid[victim]<=1;victim<=victim+1'b1;state<=PACK;
    end
    PACK:begin
     high_bits[consumed[3:0]]<=id_q[8];
     if(consumed[0])state<=WRITE_REQ;
     else begin low_id<=id_q[7:0];consumed<=consumed+1'b1;state<=TAKE;end
    end
    WRITE_REQ:if(req_ready)state<=WRITE_WAIT;
    WRITE_WAIT:if(rsp_valid)begin
     if(consumed[3:0]==15)state<=HIGH_REQ;
     else begin consumed<=consumed+1'b1;state<=TAKE;end
    end
    HIGH_REQ:if(req_ready)state<=HIGH_WAIT;
    HIGH_WAIT:if(rsp_valid)begin
     consumed<=consumed+1'b1;
     if(consumed==23039)begin
      done<=1;active<=0;epoch<=epoch==127 ? 7'd1 : epoch+1'b1;state<=IDLE;
     end else state<=TAKE;
    end
    default:;
   endcase
   if(pixel_valid && !abort_frame && !abort_pending && (!active || received==23040 || (queued==64 && !pop)))begin
    error<=1;error_code<=1;active<=0;state<=FAILED;
   end
  end
 end
endmodule
