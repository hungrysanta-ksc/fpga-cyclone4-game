// SPDX-License-Identifier: MIT
//167 ID74 >=2us SS-high: C0 raw/C1 causes/C2 decode/C3 accept/C4 counter.
// Adds one cycle to command acceptance; NOT same-edge equivalence.
// All queued stages reject SS overlap; hard faults stay live on every edge.
// MCU compares actual response bytes with its approved image before ACK.
// This is a lifecycle gate, not authentication against a malicious MCU.
module nes_rom_spi_check(
 input wire mem_clk,reset,SPI_SS,SPI_SCK,SPI_MOSI,
 output wire spi_miso,spi_selected,
 input wire load_ready,loaded,run_enable,boot_fault,
 input wire [3:0] boot_error,input wire [18:0] loaded_bytes,
 output reg load_begin,load_chr32,load_valid,load_end,start,stop,
 (* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF" *) output reg [7:0] load_data,output reg fault,output reg [3:0] error_code,
 output reg check_enable,check_request,output wire [18:0] check_address,
 input wire check_ready,check_response,check_fault,
 input wire [18:0] check_response_address,input wire [7:0] check_data);

 //471 Pipeline the independently compared response tag, not its 19-bit
 // address feedback. SPI status is sampled after >=2us, not this 1clk latency.
 // Raw reset and STOP/BEGIN cancel a queued response before publication.
 reg [18:0] check_request_tag;
 wire command_stop,command_begin;
 reg response_queued471,response_low471,response_high471;
 reg [7:0] response_data471;
 wire response_valid471=response_queued471 && !command_stop && !command_begin;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin response_queued471<=0;response_low471<=0;response_high471<=0;response_data471<=0;end
  else if(command_stop || command_begin)response_queued471<=0;
  else begin
   response_queued471<=check_response;
   if(check_response)begin
    response_low471<=check_response_address[8:0]==check_request_tag[8:0];
    response_high471<=check_response_address[18:9]==check_request_tag[18:9];
    response_data471<=check_data;
   end
  end
 end
 reg check_busy,check_done,verified;
 // Captured on queued READ; only accepted reads retain check_busy. The
 // counter cannot advance: ACK needs !busy; STOP/reset/fault clear busy.
 // Compare the live response against this immutable request tag, keeping
 // the response-edge error check outside the next-counter feedback cone.

 (* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF; -name ALLOW_SYNCH_CTRL_USAGE OFF" *) reg [18:0] check_next;
 // ACKs are separated by complete SPI frames. Precompute the low-byte carry
 // to avoid a19-bit increment chain on the command retirement edge.
 reg next_carry8;
 always @(posedge mem_clk or posedge reset)
  if(reset)next_carry8<=0;else next_carry8<=&check_next[7:0];
 (* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF; -name ALLOW_SYNCH_CTRL_USAGE OFF" *) reg [7:0] checked_data;
 assign check_address=check_next;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] ss_sync,sck_sync,mosi_sync;
 reg ss_previous,sck_previous,miso_hold;
 reg [2:0] bit_count;
 // Same-edge invariant: byte_last == (bit_count == 7). Predecode the next
 // count on the preceding SPI bit, not on the command/offset capture edge.
 reg byte_last;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)byte_last<=0;
  else if(ss_sync[1])byte_last<=0;
  else if(sck_sync[1] && !sck_previous)byte_last<=bit_count==6;
 end
 reg [3:0] byte_count;
 reg [7:0] shift,command,arg,arg_not,received_crc,tail,crc;
 reg [23:0] offset;
 reg offset_matches_next,next_below_length,next_matches_length;
 always @(posedge mem_clk or posedge reset)
  if(reset)begin offset_matches_next<=0;next_below_length<=0;next_matches_length<=0;end
  else begin
   offset_matches_next <= offset=={5'd0,check_next};
   next_below_length <= check_next<loaded_bytes;
   next_matches_length <= check_next==loaded_bytes;
  end
 // Framing and lifecycle checks are captured in parallel; effects are delayed.
 reg captured,pending;reg [3:0] decoded_error;
 reg [3:0] pending_command,pending_header_error;
 reg [4:0] pending_causes;
 wire [3:0] pending_body_error;
 reg [7:0] pending_arg;
 // Each cause is captured on the same SS-rise edge as the former encoded
 // body_error. Dynamic load_ready/fault-derived inputs are NOT sampled early.
 wire cmd60=command==8'h60,cmd61=command==8'h61,cmd62=command==8'h62;
 wire cmd63=command==8'h63,cmd64=command==8'h64,cmd66=command==8'h66;
 wire cmd67=command==8'h67,cmd68=command==8'h68,cmd69=command==8'h69;
 reg offset_zero_command,offset_length_command;
 // C0 samples external eligibility separately from command aggregation.
 // These are the original C0 values, never a prior-cycle prediction.
 reg sampled;
 reg [4:0] raw_causes;
 reg [3:0] raw_select;
 reg raw_len_command,raw_end_command,raw_len_lo_diff,raw_len_hi_diff;
 reg raw_loaded,raw_run,raw_ready,raw_load_ready;
 //224: C1 reads these only when sampled is high from the preceding C0.
 // Continuously sampling removes command decode from their capture enable,
 // without moving the consumed external values to an earlier/later edge.
 always @(posedge mem_clk or posedge reset)
  if(reset)begin raw_loaded<=0;raw_run<=0;raw_ready<=0;raw_load_ready<=0;end
  else begin raw_loaded<=loaded;raw_run<=run_enable;raw_ready<=check_ready;raw_load_ready<=load_ready;end
 wire [4:0] static_causes;
 assign static_causes[0]=command<8'h60 || command>8'h6a;
 assign static_causes[1]=(offset_zero_command && offset!=0) ||
  1'b0;
 assign static_causes[2]=((cmd60 || cmd61 || cmd62 || cmd63) && check_enable) ||
  (cmd66 && (check_enable || offset!=0)) ||
  (cmd67 && (!check_enable || check_busy || check_done || !offset_matches_next || !next_below_length));
 assign static_causes[3]=1'b0;
 assign static_causes[4]=(cmd63 && !verified) ||
  (cmd68 && (!check_enable || check_busy || !check_done || !offset_matches_next || arg!=checked_data)) ||
  (cmd69 && (!check_enable || check_busy || check_done || !next_matches_length));
 wire [4:0] sampled_causes={
  raw_causes[4] || (raw_end_command && (raw_len_lo_diff || raw_len_hi_diff)) || (raw_select[3] && (!raw_loaded || raw_run)),
  raw_select[0] && !raw_load_ready,
  raw_causes[2] || (raw_select[1] && (!raw_loaded || raw_run)) || (raw_select[2] && !raw_ready),
  raw_causes[1] || (raw_len_command && (raw_len_lo_diff || raw_len_hi_diff)),raw_causes[0]};
 // Preserve the prior error precedence: command3, offset5, lifecycle6,
 // not-ready4, verification8. Multiple causes may be captured together.
 assign pending_body_error=pending_causes[0]?4'd3:pending_causes[1]?4'd5:
  pending_causes[2]?4'd6:pending_causes[3]?4'd4:pending_causes[4]?4'd8:4'd0;
 reg [55:0] snapshot;
 wire ours=command[7:4]==4'h6;
 assign spi_selected=!reset && !SPI_SS && ours && byte_count!=0;
 assign spi_miso=miso_hold;
 function automatic [7:0] crc_byte(input [7:0] previous,input [7:0] value);
  reg [7:0] c;integer i;begin
   c=previous^value;
   for(i=0;i<8;i=i+1)c=c[7]?(c<<1)^8'h07:(c<<1);
   crc_byte=c;
  end
 endfunction
 wire [7:0] incoming={shift[6:0],mosi_sync[1]};
 wire [7:0] flags={verified,check_done,check_enable,boot_fault,fault,run_enable&&!fault,loaded&&!fault,
                   check_enable?check_busy:(load_ready&&!fault)};
 // Static command validity is captured with pending, never one edge earlier.
 reg pending_counter_clear,pending_counter_inc;
 wire counter_header_ok=byte_count==8 && bit_count==0 && crc==received_crc &&
  tail==8'ha5 && arg_not==~arg;
 // Capturing even a rejected READ is harmless: it cannot leave busy set.
 // Keep live-response error decoding out of the tag's own capture enable.
 always @(posedge mem_clk or posedge reset)
  if(reset)check_request_tag<=0;
  else if(pending && pending_command==4'h7)check_request_tag<=check_next;
 // Dynamic faults/response ownership still win on the retirement edge.
 //224: qualify each pending counter action locally, on the original edge.
 // Keep address halves independent of shared encoded error_response routing.
 wire counter_base_ok=!fault && pending && ss_sync[1] && !check_fault &&
  !(check_enable && boot_fault) && !(response_valid471 && (!check_enable || !check_busy));
 (* keep *) wire [1:0] counter_low={pending_counter_clear,pending_counter_inc} &
  {2{!response_valid471 || response_low471}};
 (* keep *) wire [1:0] counter_high={pending_counter_clear,pending_counter_inc} &
  {2{!response_valid471 || response_high471}};
 // C3 is the command acceptance boundary. C4 records the accepted
 // counter effect. Later faults do not undo an already accepted command;
 // asynchronous reset cancels the record. Counter commit remains one edge after acceptance.
 // Legal SPI observes it after >=2us SS-high, far after both edges settle.
 reg commit_clear,commit_inc;
 wire counter_commit_pending=commit_clear || commit_inc;
 always @(posedge mem_clk or posedge reset)
  if(reset)begin commit_clear<=0;commit_inc<=0;end
  else begin
   {commit_clear,commit_inc}<=counter_low & counter_high & {2{counter_base_ok}};
  end
 always @(posedge mem_clk or posedge reset)
  if(reset)check_next<=0;
  else begin
   if(commit_clear)check_next<=0;
   else if(commit_inc)begin
        // Bitwise carry prefixes keep retirement control outside the arithmetic.
        check_next[0]<=~check_next[0];
        check_next[1]<=check_next[1] ^ (&check_next[0:0]);
        check_next[2]<=check_next[2] ^ (&check_next[1:0]);
        check_next[3]<=check_next[3] ^ (&check_next[2:0]);
        check_next[4]<=check_next[4] ^ (&check_next[3:0]);
        check_next[5]<=check_next[5] ^ (&check_next[4:0]);
        check_next[6]<=check_next[6] ^ (&check_next[5:0]);
        check_next[7]<=check_next[7] ^ (&check_next[6:0]);
        check_next[8]<=check_next[8] ^ next_carry8;
        check_next[9]<=check_next[9] ^ (next_carry8 && (&check_next[8:8]));
        check_next[10]<=check_next[10] ^ (next_carry8 && (&check_next[9:8]));
        check_next[11]<=check_next[11] ^ (next_carry8 && (&check_next[10:8]));
        check_next[12]<=check_next[12] ^ (next_carry8 && (&check_next[11:8]));
        check_next[13]<=check_next[13] ^ (next_carry8 && (&check_next[12:8]));
        check_next[14]<=check_next[14] ^ (next_carry8 && (&check_next[13:8]));
        check_next[15]<=check_next[15] ^ (next_carry8 && (&check_next[14:8]));
        check_next[16]<=check_next[16] ^ (next_carry8 && (&check_next[15:8]));
        check_next[17]<=check_next[17] ^ (next_carry8 && (&check_next[16:8]));
        check_next[18]<=check_next[18] ^ (next_carry8 && (&check_next[17:8]));
   end
  end
 // Payload may change while load_valid is low, including a rejected DATA.
 // The loader consumes it only on load_valid; faults still suppress that pulse.
 always @(posedge mem_clk or posedge reset)
  if(reset)load_data<=0;
  else if(captured && pending_command==4'h1)load_data<=pending_arg;
 // Decode only command kind on the same first-byte edge as command.
 // Offset, live length, ready and faults still use their original edges.
 wire command_first_byte=!ss_sync[1] && sck_sync[1] && !sck_previous && byte_last && byte_count==0;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin command<=0;offset_zero_command<=0;offset_length_command<=0;end
  else if(ss_sync[1])begin command<=0;offset_zero_command<=0;offset_length_command<=0;end
  else if(command_first_byte)begin
   command<=incoming;
   offset_zero_command<=incoming==8'h60;
   offset_length_command<=incoming==8'h61 || incoming==8'h62 || incoming==8'h63 || incoming==8'h64;
  end
 end
 // C2 validates and decodes the command. C3 applies ONLY live fault/SS
 // gating to the pulse registers. Hard faults are not delayed.
 // Bit order: BEGIN, DATA, END, START, STOP, CHECK_READ.
 reg [5:0] approved_pulse;
 // 219: command-local half comparisons retain same-edge response checks.
 // Preserve the qualified pulse nets so synthesis need not route the shared
 // error_response node across every command output. No response pipeline.
 wire retire_base_ok=!fault && ss_sync[1] && !check_fault &&
  !(check_enable && boot_fault) && !(response_valid471 && (!check_enable || !check_busy));
 (* keep *) wire [5:0] retire_low=approved_pulse &
  {6{!response_valid471 || response_low471}};
 (* keep *) wire [5:0] retire_high=approved_pulse &
  {6{!response_valid471 || response_high471}};
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin
   approved_pulse<=0;
   load_begin<=0;load_valid<=0;load_end<=0;start<=0;stop<=0;check_request<=0;
  end else begin
   approved_pulse<=0;
   if(captured)begin
    approved_pulse[0]<=pending_header_error==0 && pending_causes==0 && pending_command==4'h0;
    approved_pulse[1]<=pending_header_error==0 && pending_causes==0 && pending_command==4'h1;
    approved_pulse[2]<=pending_header_error==0 && pending_causes==0 && pending_command==4'h2;
    approved_pulse[3]<=pending_header_error==0 && pending_causes==0 && pending_command==4'h3;
    approved_pulse[4]<=pending_header_error==0 && pending_causes==0 && pending_command==4'h4;
    approved_pulse[5]<=pending_header_error==0 && pending_causes==0 && pending_command==4'h7;
   end
   {check_request,stop,start,load_end,load_valid,load_begin}<=retire_low & retire_high & {6{retire_base_ok}};
  end
 end
 // Reachable invariant: !fault implies error_code==0. Reset establishes
 // it; every nonzero code and fault latch together. After fault both hold.
 // An explicit zero removes live-error qualification from the hold enable.
 wire error_hard=check_fault || (check_enable && boot_fault) ||
   (check_response && (!check_enable || !check_busy));
 wire error_response=response_valid471 && (!check_enable || !check_busy || (!response_low471 || !response_high471));
 wire error_overlap=(sampled || captured || pending || counter_commit_pending) && !ss_sync[1];
 always @(posedge mem_clk or posedge reset)
  if(reset)error_code<=0;
  else if(!fault)error_code<=error_hard?4'd9:error_response?4'd7:error_overlap?4'd1:pending?decoded_error:4'd0;
 // State transitions are independent of the payload write enable. All live
 // errors still clear state on THIS edge; command and counter timing is unchanged.
 wire state_error=error_hard || error_response || error_overlap || (pending && decoded_error!=0);
 assign command_stop=pending && pending_command==4;
 assign command_begin=pending && pending_command==6;
 wire command_finish=pending && pending_command==9;
 wire state_enable=(check_enable && !command_stop && !command_finish) || command_begin;
 wire state_verified=(verified && !(pending && pending_command==0) && !command_stop && !command_begin) || command_finish;
 wire state_busy=(check_busy && !response_valid471 && !command_stop && !command_begin) || (pending && pending_command==7);
 wire state_done=(check_done || response_valid471) && !command_stop && !command_begin && !(pending && pending_command==8);
 // 220: keep the two response halves local to their state destinations.
 // The original encoded-error priority and checked-data admission are intact.
 wire state_base_bad=error_hard || error_overlap || (pending && decoded_error!=0) ||
   (response_valid471 && (!check_enable || !check_busy));
 (* keep *) wire fault_response_low=response_valid471 && (!response_low471);
 (* keep *) wire fault_response_high=response_valid471 && (!response_high471);
 (* keep *) wire [3:0] state_response_low={state_done,state_busy,state_verified,state_enable} &
   {4{!response_valid471 || response_low471}};
 (* keep *) wire [3:0] state_response_high={state_done,state_busy,state_verified,state_enable} &
   {4{!response_valid471 || response_high471}};
 always @(posedge mem_clk or posedge reset)
  if(reset)fault<=0;
  else fault<=fault || state_base_bad || fault_response_low || fault_response_high;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin
   check_enable<=0;check_busy<=0;check_done<=0;verified<=0;
   checked_data<=0;load_chr32<=0;
  end else if(!fault)begin
   {check_done,check_busy,verified,check_enable}<=state_response_low & state_response_high & {4{!state_base_bad}};
   // A valid response is captured even when a queued command itself fails.
   // Hard/response/overlap errors suppress it, exactly as before.
   if(!error_hard && !error_response && !error_overlap && response_valid471)checked_data<=response_data471;
   if(!state_error && pending && pending_command==0)load_chr32<=pending_arg[0];
  end
 end
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin
   sampled<=0;raw_causes<=0;raw_select<=0;raw_len_command<=0;raw_end_command<=0;raw_len_lo_diff<=0;raw_len_hi_diff<=0;captured<=0;decoded_error<=0;pending_counter_clear<=0;pending_counter_inc<=0;pending<=0;pending_command<=0;pending_arg<=0;pending_header_error<=0;pending_causes<=0;
   ss_sync<=3;sck_sync<=0;mosi_sync<=0;ss_previous<=1;sck_previous<=0;
   bit_count<=0;byte_count<=0;shift<=0;arg<=0;arg_not<=0;
   received_crc<=0;tail<=0;crc<=0;offset<=0;snapshot<=0;miso_hold<=0;
  end else begin
   ss_sync<={ss_sync[0],SPI_SS};sck_sync<={sck_sync[0],SPI_SCK};mosi_sync<={mosi_sync[0],SPI_MOSI};
   ss_previous<=ss_sync[1];sck_previous<=sck_sync[1];
   
   // Each stage is a pulse. A transient hard fault latches fault and therefore
   // cancels the command even if it has disappeared by the retirement edge.
   pending<=captured;captured<=sampled;sampled<=0;
   if(sampled)pending_causes<=sampled_causes;
   if(captured)begin
    decoded_error<=pending_header_error!=0?pending_header_error:pending_body_error;
    pending_counter_clear<=pending_header_error==0 && pending_causes==0 &&
      (pending_command==0 || pending_command==4 || pending_command==6);
    pending_counter_inc<=pending_header_error==0 && pending_causes==0 && pending_command==8;
   end
   // A complete coherent status snapshot is held for this transaction.
   if(!ss_sync[1] && !sck_sync[1] && sck_previous)miso_hold<=(byte_count>=1 && byte_count<=7)?snapshot[55]:1'b0;
   if(ss_sync[1])begin
    miso_hold<=0;bit_count<=0;byte_count<=0;crc<=0;
    if(!ss_previous && ours && !fault && !sampled && !captured && !pending && !counter_commit_pending)begin
     sampled<=1;pending_command<=command[3:0];pending_arg<=arg;
     if(byte_count!=8 || bit_count!=0)pending_header_error<=1;
     else if(crc!=received_crc || tail!=8'ha5 || arg_not!=~arg)pending_header_error<=2;
     else if(command>8'h6a || (command!=8'h61 && command!=8'h68 && ((command==8'h60)?arg!=2:arg!=0)))pending_header_error<=3;
     else pending_header_error<=0;
     raw_causes<=static_causes;raw_select<={cmd63,cmd67,cmd66,cmd61};
     raw_len_command<=offset_length_command;raw_end_command<=cmd69;
     raw_len_lo_diff<=offset[11:0]!=loaded_bytes[11:0];
     raw_len_hi_diff<=offset[23:12]!={5'd0,loaded_bytes[18:12]};


    end
   end else if(sck_sync[1] && !sck_previous)begin
    shift<=incoming;bit_count<=bit_count+1'b1;
    if(byte_count>=1 && byte_count<=7)snapshot<={snapshot[54:0],1'b0};
    if(byte_last)begin
     if(byte_count!=9)byte_count<=byte_count+1'b1;
     if(byte_count<6)crc<=crc_byte(crc,incoming);
     case(byte_count)
      0:begin 
       if(incoming==8'h6a)snapshot<={8'h78,flags,checked_data,5'd0,check_next,error_code,boot_error};
       else snapshot<={8'h78,flags,{4'd0,error_code},5'd0,loaded_bytes,{4'd0,boot_error}};
      end
      1:offset[23:16]<=incoming;2:offset[15:8]<=incoming;3:offset[7:0]<=incoming;
      4:arg<=incoming;5:arg_not<=incoming;6:received_crc<=incoming;7:tail<=incoming;
      default:;
     endcase
    end
   end
  end
 end
endmodule
