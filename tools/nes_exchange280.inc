 // Shared request fields replace source/plan args and queue CRC state.
 reg [15:0] request_length280,request_value280,payload_crc280;
 reg [7:0] request_number280;
 reg crc_good280,tail_good280;
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
   request_length280<=0;request_value280<=0;request_number280<=0;
   crc_good280<=0;tail_good280<=0;payload_crc280<=16'hffff;
  end else if(byte_event)begin
   if((count==0&&incoming==8'he1)||command==8'he1)
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
     default:;
    endcase
   end
  end
 end
