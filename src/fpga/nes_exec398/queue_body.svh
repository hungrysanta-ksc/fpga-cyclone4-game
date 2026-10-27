// SPDX-License-Identifier: MIT
// Physical two-slot storage. Identity and SS completion are executed by the
// common host program; an unpublished slot is never visible to its consumer.
 (* ramstyle="M9K" *) reg[7:0] buffer[0:1023];
 reg[15:0] accepted,retired,consumed312,sequence312;reg reserved398;
 reg[8:0] lengths394[0:1];reg[7:0] read_data;
 wire[7:0] command=link270[32:25],incoming=link270[24:17];
 wire[9:0] count=link270[16:7];wire[2:0] bits=link270[6:4];
 wire byte_event=link270[110],ending=link270[109],ss=link270[3];
 wire ours=command==8'he0||command==8'he1||command==8'he2;
 wire empty315=accepted[1:0]==retired[1:0];
 wire[2:0]used=accepted[2:0]-retired[2:0]+reserved398;
 wire full=accepted[1:0]==(retired[1:0]^2'b10);
 wire can_write=link270[113];
 wire[9:0] read_at=expected_select313?{1'b0,expected_address313}:{1'b1,retired[0],sn_address};
 always @(posedge clk)begin
  read_data<=buffer[read_at];
  if(expected_write313&&expected_select313&&expected_address313<472&&enable&&!reset&&!fault)
   buffer[read_at]<=expected_data313;
 end
 // Separate RTL processes describe the two physical RAM ports. Combining
 // both writes with the read in one process expands this RAM into flip-flops.
 always @(posedge clk)if(!reset&&!fault&&enable&&byte_event&&command==8'he1&&can_write&&count>=1&&count<=256)
  buffer[{1'b1,accepted[0],count[7:0]-8'd1}]<=incoming;
 assign sn_data=read_data;assign storage_empty312=empty315&&!reserved398;
 assign packet_ready=!empty315&&enable&&!reset&&!fault;
 assign packet_length=packet_ready?lengths394[retired[0]]:9'd0;
 assign record_valid312=0;assign record_at312=0;assign record_byte312=0;
 assign selected=!reset&&!SPI_SS&&ours&&count!=0;assign miso=link270[107];assign crc_take270=0;
 assign status270={consumed312,8'hfc,{fault,4'd0,full||reserved398,1'b0,!empty315},accepted,retired,progress_status,8'd0};
 assign admit319=enable&&!full&&!reserved398&&!fault;
 reg event_valid,event_end;reg[9:0]event_count;reg[7:0]event_value,event_crc8;reg[2:0]event_flags;reg[15:0]event_length,event_received;
 wire plan_ours=command==8'he8||command==8'he9||command==8'hea;
 wire source_ours=command==8'hd4||command==8'hd5;
 wire header_event=byte_event&&(count==0&&(incoming==8'he0||incoming==8'he1||incoming==8'he2||incoming==8'he8||incoming==8'he9||incoming==8'hea||incoming==8'hd4||incoming==8'hd5)||command==8'he1&&count>=3&&count<=10||command==8'he9&&(count<=3||count>=link270[106:91]+4&&count<=link270[106:91]+5)||source_ours&&count<=5||command==8'hea&&(count<14||!link270[112]||count<12+{link270[93:91],1'b0}));
 wire ending_event=ending&&(ours||plan_ours);
 assign irq398=event_valid;
 always @*case(control_address398)
  112:control_q398={7'd0,event_valid};113:control_q398=event_end?8'd2:8'd1;
  114:control_q398=event_count[7:0];115:control_q398={6'd0,event_count[9:8]};
  116:control_q398=event_value;117:control_q398={5'd0,event_flags};
  118:control_q398=event_length[7:0];119:control_q398=event_length[15:8];
  120:control_q398=sequence312[7:0];121:control_q398=sequence312[15:8];
  124:control_q398=event_received[7:0];125:control_q398=event_received[15:8];
  126:control_q398=event_crc8;
  default:control_q398=0;
 endcase
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   accepted<=0;retired<=0;consumed312<=0;sequence312<=0;fault<=0;reserved398<=0;
   event_valid<=0;event_end<=0;event_count<=0;event_value<=0;event_flags<=0;event_length<=0;event_received<=0;event_crc8<=0;
  end else if(enable&&!fault)begin
   if(frame_start312)sequence312<=0;
   // Reserve at the physical command edge. Deferred program validation must
   // not expose a credit before this unpublished packet has been committed.
   if(byte_event&&count==0&&incoming==8'he1&&admit319)reserved398<=1;
   if(consume_record312)consumed312<=consumed312+1'b1;
   if(parser_retire)begin if(!packet_ready)fault<=1;else retired<=retired+1'b1;end
   if(control_write398&&control_address398==123)event_valid<=0;
   if(control_write398&&control_address398==122)begin
    if(!event_valid||!event_end||event_value!=8'he1||full||!reserved398)fault<=1;
    else begin accepted<=accepted+1'b1;sequence312<=sequence312+1'b1;lengths394[accepted[0]]<=event_count-3;reserved398<=0;end
   end
   if(header_event||ending_event)begin
    if(event_valid&&!(control_write398&&control_address398==123))fault<=1;
    else begin
     event_valid<=1;event_end<=ending_event;event_count<=count;event_value<=ending_event?command:incoming;
     event_flags<={can_write,bits==0,link270[108]};event_length<=link270[106:91];event_received<=link270[90:75];event_crc8<=link270[48:41];
    end
   end
  end
 end
endmodule
