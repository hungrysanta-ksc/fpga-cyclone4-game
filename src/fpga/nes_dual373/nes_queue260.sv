// SPDX-License-Identifier: MIT
// Two immutable 256-byte packets; one host-clock lifetime, COMMON reset only.
// E0 status20: dummy,F7,flags,acceptedBE16,retiredBE16,ACK12,CRC8.
// E1 stays command+16..256 packet bytes+CRC16BE. F6 clients must reject F7.
// Admission/ordered ACK identity is owned by the flow; only parser_retire releases credit.
module nes_queue260(
 output wire admit319,input wire [113:0] link270,output wire [199:0] status270,output wire crc_take270,

 input wire [127:0] progress_status,
 input wire frame_start312,input wire [31:0] frame_serial312,
 input wire [15:0] frame_generation312,input wire [191:0] record312,input wire load_enable312,input wire [3:0] load_at315,output wire storage_empty312,
 output wire record_valid312,output wire [4:0] record_at312,output wire [7:0] record_byte312,
 input wire expected_select313,expected_write313,
 input wire [8:0] expected_address313,input wire [7:0] expected_data313,
 input wire parser_retire,input wire consume_record312,
 input wire clk,reset,enable,SPI_SS,SPI_SCK,SPI_MOSI,
 output wire selected,miso,
 input wire [7:0] sn_address,output wire [7:0] sn_data,
 output wire packet_ready,output wire [8:0] packet_length,
 output reg fault
);
 (* ramstyle="M9K" *) reg [7:0] buffer[0:1023];
 reg [15:0] accepted,retired,consumed312;
 reg [15:0] sequence312;wire [15:0] ingress_length312=link270[106:91];
 reg bad_header312;
 // Expected RAM owns 0..471; packet slots own 512..767/768..1023.
 // Preserve the wire packet. Only the active-record loader reorders fields.
 wire [15:0] encoded312=record312[79:64];
 function automatic [7:0] identity312(input [3:0] i);
  case(i)
   2:identity312=sequence312[7:0];3:identity312=sequence312[15:8];
   4:identity312=frame_serial312[7:0];5:identity312=frame_serial312[15:8];
   6:identity312=frame_serial312[23:16];7:identity312=frame_serial312[31:24];
   8:identity312=frame_generation312[7:0];9:identity312=frame_generation312[15:8];
   default:identity312=0;
  endcase
 endfunction
 
 wire [2:0] used=accepted[2:0]-retired[2:0];
 wire empty315=accepted[1:0]==retired[1:0];
 wire full=accepted[1:0]==(retired[1:0]^2'b10);
 reg [7:0] read_data;
 wire [7:0] read_address=sn_address;
 wire [9:0] read_address312=expected_select313?{1'b0,expected_address313}:{1'b1,retired[0],(load_enable312?(load_at315<4?{4'd0,load_at315}:{4'd0,load_at315}+8'd6):sn_address)};
 always @(posedge clk)begin
  read_data<=buffer[read_address312];
  if(expected_write313&&expected_select313&&expected_address313<472&&enable&&!reset&&!fault)
   buffer[read_address312]<=expected_data313;
 end
 assign record_valid312=load_enable312&&load_at315!=0&&!reset&&!fault;
 assign record_at312={1'b0,load_at315}-1'b1;assign record_byte312=read_data;
 assign sn_data=read_data;
 assign storage_empty312=empty315;
 assign packet_ready=!empty315&&enable&&!reset&&!fault;
 assign packet_length=packet_ready?encoded312[8:0]+9'd16:9'd0;
 wire [7:0] common_crc270,status_reply270,command,incoming;
 wire [9:0] count270;wire [2:0] bits270;wire [1:0] ss,sck;wire prev_ss,prev_sck;
 assign {common_crc270,status_reply270,command,incoming,count270,bits270,ss[1],sck[1],prev_ss,prev_sck}=link270[48:0];
 assign ss[0]=1'b0;assign sck[0]=1'b0;
 wire [8:0] byte_count=count270>511?9'd511:count270[8:0];wire [2:0] bit_count=bits270;
 wire can_write=link270[113];wire [15:0] request_crc=link270[64:49];


 wire [7:0] ingress_offset338=byte_count[7:0]-8'd1;
 wire write312=!reset&&!fault&&enable&&!ss[1]&&sck[1]&&!prev_sck&&
  bit_count==7&&command==8'he1&&can_write&&byte_count!=0&&byte_count<=256;
 wire [9:0] write_address312={1'b1,accepted[0],ingress_offset338};
 wire [7:0] write_data312=incoming;
 always @(posedge clk)if(write312)buffer[write_address312]<=write_data312;
 wire ours=command==8'he0||command==8'he1||command==8'he2;
 wire [7:0] flags={fault,4'd0,full,1'b0,(!empty315)};

 assign selected=!reset&&!SPI_SS&&ours&&byte_count!=0;
 assign miso=link270[107];

 always @(posedge clk or posedge reset)begin
  if(reset)begin
   accepted<=0;retired<=0;consumed312<=0;fault<=0;
   sequence312<=0;bad_header312<=0;


   

  end else begin
   


   if(frame_start312)sequence312<=0;
   if(consume_record312&&enable&&!fault)consumed312<=consumed312+1'b1;
   if(parser_retire&&enable&&!fault)begin
    if(!packet_ready)fault<=1;else begin retired<=retired+1'b1;end
   end

   if(ss[1])begin
    
    if(link270[109]&&ours)begin
     if(command==8'he0||command==8'he2)begin if(byte_count!=(command==8'he2 ? 14 : 25)||bit_count!=0)fault<=1;end
     else if(!can_write||!enable||fault||bad_header312||sequence312==65535||ingress_length312!={7'd0,byte_count}-16'd19||!link270[108])fault<=1;
     else begin accepted<=accepted+1'b1;sequence312<=sequence312+1'b1;end
    end
   end else if(sck[1]&&!prev_sck)begin
    
    if(bit_count==7)begin
     if(byte_count==0)begin
      
      bad_header312<=0;


      
      
      

     end else if(command==8'he1)begin

      if(can_write&&!fault&&byte_count<=256)begin
       if(byte_count<=16)begin
        if(byte_count>=3&&byte_count<=10&&incoming!=identity312(byte_count-1))bad_header312<=1;
        
        
        
       end
      end

     end
    end
   end
  end
 end

 assign crc_take270=1'b0;
 assign status270={consumed312,8'hfc,flags,accepted,retired,progress_status,8'd0};
assign admit319=enable&&!full&&!fault;
endmodule
