// SPDX-License-Identifier: MIT
// One host-clock SPI receiver and immutable status snapshot for all owners.
// Endpoint ownership, admission, RAM and retirement remain explicit.
module nes_spi270(input wire clk,reset,SPI_SS,SPI_SCK,SPI_MOSI,
 input wire [183:0] source_status,output_status,plan_status,
 input wire request_crc_enable,output wire [48:0] link);
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] ss,sck,mosi;
 reg prev_ss,prev_sck;reg [2:0] bits;reg [9:0] count;
 reg [7:0] shift,command,request_crc,status_crc;
 reg [183:0] snapshot;reg [4:0] status_length,crc_at;reg crc_busy;
 wire [7:0] incoming={shift[6:0],mosi[1]};
 wire byte_event=!ss[1]&&sck[1]&&!prev_sck&&bits==7;
 wire request_step=byte_event&&request_crc_enable;
 wire [7:0] crc_previous=request_step?request_crc:status_crc;
 wire [7:0] crc_byte=request_step?incoming:snapshot[183-crc_at*8-:8];
 function automatic [7:0] c8(input [7:0] c0,input [7:0] b);
  reg [7:0] c;integer j;begin c=c0^b;for(j=0;j<8;j=j+1)c=c[7]?(c<<1)^8'h07:c<<1;c8=c;end
 endfunction
 wire [7:0] crc_next=c8(crc_previous,crc_byte);
 wire [7:0] reply=count==status_length?status_crc:
  (count>=1&&count<status_length)?snapshot[183-(count-1)*8-:8]:8'd0;
 assign link={request_crc,reply,command,incoming,count,bits,ss[1],sck[1],prev_ss,prev_sck};
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   ss<=3;sck<=0;mosi<=0;prev_ss<=1;prev_sck<=0;bits<=0;count<=0;shift<=0;command<=0;
   request_crc<=0;status_crc<=0;snapshot<=0;status_length<=0;crc_at<=0;crc_busy<=0;
  end else begin
   ss<={ss[0],SPI_SS};sck<={sck[0],SPI_SCK};mosi<={mosi[0],SPI_MOSI};prev_ss<=ss[1];prev_sck<=sck[1];
   if(request_step)request_crc<=crc_next;
   else if(crc_busy)begin
    status_crc<=crc_next;
    if(crc_at==status_length-2)crc_busy<=0;
    else crc_at<=crc_at+1'b1;
   end
   if(ss[1])begin bits<=0;count<=0;command<=0;request_crc<=0;crc_busy<=0;end
   else if(sck[1]&&!prev_sck)begin
    shift<=incoming;bits<=bits+1'b1;
    if(bits==7)begin
     if(count!=1023)count<=count+1'b1;
     if(count==0)begin
      command<=incoming;status_crc<=0;crc_at<=0;crc_busy<=1;
      case(incoming)
       8'hd0,8'hd2,8'hd3:begin snapshot<=source_status;status_length<=7;end
       8'he0:begin snapshot<=output_status;status_length<=23;end
       8'he2:begin snapshot<={8'hf9,output_status[175:128],8'd0,120'd0};status_length<=8;end
       8'he8:begin snapshot<=plan_status;status_length<=19;end
       default:begin snapshot<=0;status_length<=0;crc_busy<=0;end
      endcase
     end
    end
   end
  end
 end
endmodule
