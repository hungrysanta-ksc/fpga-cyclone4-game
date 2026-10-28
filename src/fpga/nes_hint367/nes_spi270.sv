// SPDX-License-Identifier: MIT
// One host-clock SPI receiver and immutable status snapshot for all owners.
// Endpoint ownership, admission, RAM and retirement remain explicit.
module nes_spi270(input wire clk,reset,SPI_SS,SPI_SCK,SPI_MOSI,
 input wire [199:0] source_status,output_status,plan_status,
 output wire progress_irq284,output reg progress_mode284,output reg source_mode367,
 input wire request_crc_enable,input wire queue_admit319,plan_admit319,output wire [113:0] link);
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] ss,sck,mosi;
 reg prev_ss,prev_sck;reg [2:0] bits;reg [9:0] count;
 reg [7:0] shift,command,request_crc,status_crc;
 reg [7:0] reply_byte315;
 reg [199:0] snapshot;reg [4:0] status_length,crc_at;reg crc_busy;
 reg [48:0] progress_key331;
 wire [48:0] live_key331={output_status[175],output_status[151:128],plan_status[167:160],output_status[199:184]};
 wire [7:0] incoming={shift[6:0],mosi[1]};
 wire byte_event=!ss[1]&&sck[1]&&!prev_sck&&bits==7;
 wire request_step=byte_event&&request_crc_enable;
 wire [7:0] crc_previous=request_step?request_crc:status_crc;
 // CRC and transmission use the same byte lane. Rotate all25 bytes
 // during the pre-response CRC pass, restoring the original byte order.
 wire [7:0] crc_byte=request_step?incoming:snapshot[199:192];
 function automatic [7:0] c8(input [7:0] c0,input [7:0] b);
  reg [7:0] c;integer j;begin c=c0^b;for(j=0;j<8;j=j+1)c=c[7]?(c<<1)^8'h07:c<<1;c8=c;end
 endfunction
 wire [7:0] crc_next=c8(crc_previous,crc_byte);
 wire [7:0] reply=reply_byte315;
 // Compare only autonomous progress: retirement, phase and plan flags.
 // accepted counters change on ARM writes, and cannot authorize a wake/credit.
 reg armed284;
 assign progress_irq284=armed284&&(live_key331!=progress_key331);
 reg transaction_admit319;
 assign link[113]=transaction_admit319;
 always @(posedge clk or posedge reset)begin
  if(reset)transaction_admit319<=0;
  else if(ss[1])transaction_admit319<=0;
  else if(byte_event&&count==0)transaction_admit319<=
   incoming==8'he1 ? queue_admit319 : incoming==8'he9 ? plan_admit319 : 1'b0;
 end
 reg reply_bit282;
 assign link[107]=reply_bit282;
 always @(posedge clk or posedge reset)begin
  if(reset)reply_bit282<=0;
  else if(ss[1])reply_bit282<=0;
  else if(!sck[1]&&prev_sck)reply_bit282<=reply[7-bits];
 end
 assign link[48:0]={request_crc,reply,command,incoming,count,bits,ss[1],sck[1],prev_ss,prev_sck};
 // Shared request fields replace source/plan args and queue CRC state.
 reg [15:0] request_length280,request_value280,payload_crc280;
 reg [7:0] request_number280;
 reg crc_good280,tail_good280;
 wire plan_payload314=command==8'he9&&count>=4&&count<=request_length280+3;
 assign link[110]=byte_event;
 assign link[111]=plan_payload314;
 assign link[112]=command==8'he9&&count==3&&
  (request_length280<3||request_length280>512||incoming==0||incoming>16);
 assign link[109]=ss[1]&&!prev_ss;
 assign link[108]=bits==0&&
   (command==8'he1 ? (count>=19&&count<=259&&payload_crc280==0):
    command==8'he9 ? (request_length280>=3&&request_length280<=512&&request_number280>=1&&request_number280<=16&&
      count==request_length280+8&&crc_good280&&tail_good280&&request_value280==payload_crc280):
    command==8'hea ? ((count==7&&crc_good280&&tail_good280)||(count==28&&request_value280==payload_crc280)):1'b0);
 assign link[106:49]={request_length280,request_value280,request_number280,
                     crc_good280,tail_good280,payload_crc280};
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer j;begin c=c0^{b,8'd0};
   for(j=0;j<8;j=j+1)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end
 endfunction
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   request_length280<=0;request_value280<=0;request_number280<=0;
   crc_good280<=0;tail_good280<=0;payload_crc280<=16'hffff;
  end else if(ss[1])begin
   // The sealed request fields outlive SS for the next-cycle RAM handoff.
   crc_good280<=0;tail_good280<=0;payload_crc280<=16'hffff;
  end else if(byte_event)begin
   if(count==0)begin request_length280<=0;request_value280<=0;request_number280<=0;end
   if((count==0&&(incoming==8'he1||incoming==8'hea))||command==8'he1||plan_payload314||(command==8'hea&&count<26))
    payload_crc280<=c16(payload_crc280,incoming);
   if(command==8'hd4||command==8'hd5)begin
    case(count)
     1:request_value280[15:8]<=incoming;2:request_value280[7:0]<=incoming;
     3:request_length280[7:0]<=incoming;4:request_length280[15:8]<=incoming;
     5:request_number280<=incoming;6:crc_good280<=incoming==request_crc;
     7:tail_good280<=incoming==8'ha5;
     default:;
    endcase
   end else if(command==8'he9)begin
    if(count==1)request_length280[7:0]<=incoming;
    else if(count==2)request_length280[15:8]<=incoming;
    else if(count==3)request_number280<=incoming;
    else if(count==request_length280+4)request_value280[15:8]<=incoming;
    else if(count==request_length280+5)request_value280[7:0]<=incoming;
    else if(count==request_length280+6)crc_good280<=incoming==request_crc;
    else if(count==request_length280+7)tail_good280<=incoming==8'ha5;
   end else if(command==8'hea)begin
    case(count)
     1:request_length280[7:0]<=incoming;2:request_length280[15:8]<=incoming;
     3:request_value280[15:8]<=incoming;4:request_value280[7:0]<=incoming;
     5:crc_good280<=incoming==request_crc;6:tail_good280<=incoming==8'ha5;
     26:request_value280[7:0]<=incoming;27:request_value280[15:8]<=incoming;
     default:;
    endcase
   end
  end
 end

 always @(posedge clk or posedge reset)begin
  if(reset)begin
   ss<=3;sck<=0;mosi<=0;prev_ss<=1;prev_sck<=0;bits<=0;count<=0;shift<=0;command<=0;
   progress_key331<=0;armed284<=0;progress_mode284<=0;source_mode367<=0;request_crc<=0;status_crc<=0;snapshot<=0;status_length<=0;crc_at<=0;crc_busy<=0;reply_byte315<=0;
  end else begin
   ss<={ss[0],SPI_SS};sck<={sck[0],SPI_SCK};mosi<={mosi[0],SPI_MOSI};prev_ss<=ss[1];prev_sck<=sck[1];
   if(request_step)request_crc<=crc_next;
   else if(crc_busy&&!byte_event)begin
    snapshot<={snapshot[191:0],snapshot[199:192]};
    if(crc_at<status_length-1)status_crc<=crc_next;
    if(crc_at==24)crc_busy<=0;
    else crc_at<=crc_at+1'b1;
   end
   if(ss[1])begin reply_byte315<=0;bits<=0;count<=0;command<=0;request_crc<=0;crc_busy<=0;end
   else if(sck[1]&&!prev_sck)begin
    shift<=incoming;bits<=bits+1'b1;
    if(bits==7)begin
     if(count!=0)begin
      if(count+1==status_length)reply_byte315<=status_crc;
      else if(count+1<status_length)reply_byte315<=snapshot[191:184];
      else reply_byte315<=0;
      snapshot<={snapshot[191:0],snapshot[199:192]};
     end
     if(count!=1023)count<=count+1'b1;
     if(count==0)begin
      progress_key331<=live_key331;
      armed284<=incoming==8'he2||incoming==8'he8||incoming==8'he1||incoming==8'he9;
      if(incoming==8'hd4||incoming==8'hd5)source_mode367<=1;
      else if(incoming!=8'hea)source_mode367<=0;
      if(incoming==8'he2||incoming==8'he8)progress_mode284<=1;
      else if(incoming==8'hd0||incoming==8'hd2||incoming==8'hd3||incoming==8'hd4||incoming==8'hd5)progress_mode284<=0;
      command<=incoming;status_crc<=0;crc_at<=0;crc_busy<=1;
      case(incoming)
       8'hd0,8'hd2,8'hd3:begin reply_byte315<=source_status[183:176];snapshot<={source_status[183:0],16'd0};status_length<=7;end
       8'he0:begin reply_byte315<=8'hfb;snapshot<={8'hfb,output_status[175:128],plan_status[167:144],output_status[199:184],output_status[127:96],output_status[63:8],16'd0};status_length<=24;end
       8'he1,8'he9,8'he2,8'he8:begin
        reply_byte315<=8'hfb;snapshot<={8'hfb,output_status[175:128],plan_status[167:144],output_status[199:184],104'd0};status_length<=13;
       end
       default:begin reply_byte315<=0;snapshot<=0;status_length<=0;crc_busy<=0;end
      endcase
     end
    end
   end
  end
 end
endmodule
