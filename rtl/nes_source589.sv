// SPDX-License-Identifier: MIT
// Bounded R2 source: frozen586 blocks, one NES-owned synchronous byte RAM.
// Nonmap selection re-queries the immutable lease; CRC runs only on LOAD.
module nes_source589 #(parameter MAX_CYCLES=33554432)(
 input wire clk,reset,enable,frame_owned,geometry_valid,
 input wire [15:0] frame_generation,input wire [31:0] content_epoch,
 input wire [5:0] group_count,palette_count,input wire [7:0] object_count,exception_count,row_count,
 input wire [2:0] patch_count,
 output wire query,output wire [2:0] query_kind,output reg [12:0] query_index,
 output wire [15:0] query_generation,input wire response,hit,input wire [63:0] data,
 output wire block_valid,input wire block_ready,output reg [8:0] block_length,output reg block_seal,
 output wire byte_valid,input wire byte_ready,output reg [7:0] byte_data,
 input wire packet_sent,input wire ack_valid,ack_accept,input wire [15:0] ack_generation,
 output reg release_frame,output reg [3:0] fault,output wire busy
);
 localparam IDLE=0,CONTROL=1,BLOCK=2,PUT=3,AFTER=4,SECTION=5,DECIDE=6,QWAIT=7,QDONE=8,
  REPEAT=9,RASTER=10,LITERAL=11,LITPAIR=12,LOAD=13,LOADED=14,STORE=15,STORED=16,
  RAMWAIT=17,RAMGET=18,WRITE=19,COMPARE=20,CURLO=21,CURHI=22,OLDLO=23,OLDHI=24,
  CHOOSE=25,COPY=26,COPYREAD=27,COPYNEXT=28,HEADER=29,PREFIX=30,BODY=31,BODYREAD=32,
  BODYNEXT=33,NEXTBLOCK=34,META=35,PREPARE=36,COMMITWAIT=37,DRAIN=38,STOPPED=39,BODYADV=40;
 reg [5:0] state,ret,byte_ret,query_ret;
 (* ramstyle="M9K" *) reg [7:0] mem[0:3071];
 reg [11:0] addr;reg [7:0] wr,rd,mval;
 always @(posedge clk)begin rd<=mem[addr];if(state==WRITE&&!reset&&enable&&frame_owned)mem[addr]<=wr;end
 reg [15:0] generation,counts[0:5],at,n,loaded,records,crc,canonical_length,old_count;
 reg [31:0] epoch,serial,cycles;reg valid_base,inherit;
 reg [2:0] kind,patches,mode;reg [3:0] width,lane;
 reg [63:0] value,first,previous,pair;
 reg [5:0] pos;reg [8:0] body_at,body_count;
 reg [1:0] shift_pass,chosen;reg [32:0] masks[0:2];reg [5:0] differences[0:2];
 reg [15:0] current_word;reg [7:0] low;reg [5:0] item;reg [7:0] control_index;
 reg [1:0] control_kind; // BEGIN, META, END, COMMIT
 reg [8:0] best_size;reg [15:0] limit;reg [8:0] cap;
 wire live=!reset&&enable&&frame_owned&&geometry_valid&&frame_generation==generation&&content_epoch==epoch;
 assign busy=state!=IDLE;
 assign query=state==DECIDE&&live;
 assign query_kind=kind==6?3'd7:kind;
 assign query_generation=generation;
 assign block_valid=state==BLOCK&&live;
 assign byte_valid=state==PUT&&live;
 function automatic [15:0] c16(input [15:0] c,input [7:0] b);
  reg [15:0] t;integer i;begin t=c^{b,8'd0};for(i=0;i<8;i=i+1)t=t[15]?(t<<1)^16'h1021:t<<1;c16=t;end
 endfunction
 function automatic [63:0] next_y(input [63:0] v);
  reg [14:0] t;begin t=v[14:0];if(t[14:12]!=7)t=t+15'h1000;
   else begin t[14:12]=0;if(t[9:5]==29)begin t[9:5]=0;t[11]=!t[11];end
    else if(t[9:5]==31)t[9:5]=0;else t[9:5]=t[9:5]+1'b1;end next_y={v[63:15],t};end
 endfunction
 always @*begin
  limit=kind==6?{5'd0,patches,8'd0}:counts[kind<6?kind:0];
  case(kind)0:begin width=2;cap=33;end 1:begin width=1;cap=32;end
   2,4:begin width=7;cap=32;end 3:begin width=4;cap=56;end default:begin width=1;cap=224;end endcase
 end
 task readmem(input [11:0] a,input [5:0] back);begin addr<=a;ret<=back;state<=RAMWAIT;end endtask
 task writemem(input [11:0] a,input [7:0] b,input [5:0] back);begin addr<=a;wr<=b;ret<=back;state<=WRITE;end endtask
 task ask(input [15:0] index,input [5:0] back);begin query_index<=index[12:0];query_ret<=back;state<=DECIDE;end endtask
 task emitbyte(input [7:0] b,input [5:0] back);begin byte_data<=b;byte_ret<=back;state<=PUT;end endtask
 task bad(input [3:0] why);begin fault<=why;valid_base<=0;release_frame<=1;state<=STOPPED;end endtask
 integer j;
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;fault<=0;release_frame<=0;generation<=0;epoch<=0;serial<=0;cycles<=0;valid_base<=0;inherit<=0;old_count<=0;
   at<=0;n<=0;kind<=0;patches<=0;records<=0;crc<=16'hffff;canonical_length<=0;query_index<=0;
   value<=0;first<=0;previous<=0;pair<=0;lane<=0;pos<=0;body_at<=0;body_count<=0;loaded<=0;
   addr<=0;wr<=0;mval<=0;ret<=0;byte_ret<=0;query_ret<=0;byte_data<=0;block_length<=0;block_seal<=0;
   shift_pass<=0;chosen<=0;current_word<=0;low<=0;item<=0;control_index<=0;control_kind<=0;best_size<=0;mode<=0;
   for(j=0;j<6;j=j+1)counts[j]<=0;
   for(j=0;j<3;j=j+1)begin masks[j]<=0;differences[j]<=0;end
  end else begin
   release_frame<=0;
   if(state!=IDLE&&state!=DRAIN&&state!=STOPPED)cycles<=cycles+1'b1;
   if(state!=IDLE&&state!=DRAIN&&state!=STOPPED&&(!live||cycles>=MAX_CYCLES))bad(1);
   else case(state)
    IDLE:if(enable&&frame_owned)begin
     if(!geometry_valid||!content_epoch||row_count!=224||!group_count||group_count>32||!palette_count||palette_count>2||object_count>128||exception_count>128||serial==32'hffffffff)bad(2);
     else begin
      generation<=frame_generation;epoch<=content_epoch;inherit<=valid_base&&epoch==content_epoch;cycles<=0;
      counts[0]<=group_count*33;counts[1]<=224;counts[2]<=object_count;counts[3]<=exception_count;counts[4]<=224;counts[5]<=palette_count*32;
      patches<=patch_count;records<=0;crc<=16'hffff;canonical_length<=0;kind<=0;at<=0;control_kind<=0;control_index<=0;
      block_length<=32;block_seal<=0;ret<=CONTROL;state<=BLOCK;
     end
    end
    BLOCK:if(block_ready)state<=ret;
    PUT:if(byte_ready)state<=byte_ret;
    RAMWAIT:state<=RAMGET;
    RAMGET:begin mval<=rd;state<=ret;end
    WRITE:state<=ret;
    DECIDE:state<=QWAIT;
    QWAIT:if(response)begin if(!hit)bad(3);else begin value<=data;state<=query_ret;end end
    CONTROL:begin
     if(control_kind==0)begin
      case(control_index)
       0:emitbyte(8'h82,AFTER);1:emitbyte(8'h05,AFTER);2:emitbyte(1,AFTER);3:emitbyte({7'd0,inherit},AFTER);
       4,5,6,7:emitbyte(epoch>>((control_index-4)*8),AFTER);
       8,9,10,11:emitbyte((serial+1)>>((control_index-8)*8),AFTER);
       12,13,14,15:emitbyte((inherit?serial:32'd0)>>((control_index-12)*8),AFTER);
       16:emitbyte(generation[7:0],AFTER);17:emitbyte(generation[15:8],AFTER);
       30:emitbyte({5'd0,patches},AFTER);31:emitbyte(0,AFTER);
       default:emitbyte(counts[(control_index-18)>>1]>>((control_index&1)*8),AFTER);
      endcase
     end else case(control_index)
      0:emitbyte(control_kind==1?4:control_kind==2?1:3,AFTER);1:emitbyte(8'hf0,AFTER);
      2:emitbyte(control_kind==3?generation[7:0]:canonical_length[7:0],AFTER);
      3:emitbyte(control_kind==3?generation[15:8]:canonical_length[15:8],AFTER);
      4,5:emitbyte(control_kind==3?((serial+1)>>((control_index-4)*8)):(records>>((control_index-4)*8)),AFTER);
      6,7:emitbyte(control_kind==3?((serial+1)>>((control_index-4)*8)):(crc>>((control_index-6)*8)),AFTER);
     endcase
    end
    AFTER:if(control_index+1==(control_kind==0?32:8))begin
     control_index<=0;
     case(control_kind)0:state<=SECTION;1:begin kind<=6;at<=0;state<=SECTION;end
      2:state<=PREPARE;3:state<=COMMITWAIT;endcase
    end else begin control_index<=control_index+1'b1;state<=CONTROL;end
    SECTION:if(at==limit)begin
     at<=0;
     if(kind==5||kind==6)begin control_kind<=kind==5?1:2;control_index<=0;block_length<=8;block_seal<=1;ret<=CONTROL;state<=BLOCK;end
     else kind<=kind+1'b1;
    end else if(kind<2)begin
     n<=limit-at<cap?limit-at:cap;loaded<=0;mode<=0;state<=LOAD;
    end else begin n<=1;ask(at,QDONE);end
    QDONE:begin first<=value;previous<=value;if(at+1==limit)begin mode<=0;loaded<=0;state<=LOAD;end else ask(at+1,REPEAT);end
    REPEAT:if(value==first&&n<256)begin
     n<=n+1'b1;
     if(at+n+1==limit||n==255)begin mode<=1;loaded<=0;state<=LOAD;end else ask(at+n+1,REPEAT);
    end else if(n>=2)begin mode<=1;loaded<=0;state<=LOAD;end
    else if(kind==4)begin previous<=first;ask(at+1,RASTER);end
    else begin n<=1;state<=LITERAL;end
    RASTER:if(value==next_y(previous)&&n<256)begin
     previous<=value;n<=n+1'b1;
     if(at+n+1==limit||n==255)begin mode<=2;loaded<=0;state<=LOAD;end else ask(at+n+1,RASTER);
    end else if(n>=2)begin mode<=2;loaded<=0;state<=LOAD;end
    else begin n<=1;state<=LITERAL;end
    LITERAL:if(n==cap||at+n==limit)begin mode<=0;loaded<=0;state<=LOAD;end
     else if(at+n+1==limit)begin n<=n+1'b1;end
     else ask(at+n,LITPAIR);
    LITPAIR:begin pair<=value;ask(at+n+1,META);end
    META:if(value==pair||(kind==4&&value==next_y(pair)))begin mode<=0;loaded<=0;state<=LOAD;end
     else begin n<=n+1'b1;state<=LITERAL;end
    LOAD:if(loaded==n)begin
     if(kind<2)begin
      item<=0;shift_pass<=0;
      for(j=0;j<3;j=j+1)begin masks[j]<=0;differences[j]<=0;end
      if(inherit&&(kind==1||at+n<=old_count))state<=COMPARE;
      else begin mode<=0;body_at<=0;state<=COPY;end
     end else begin body_count<=mode==0?n*width:width;block_length<=6+(mode==0?n*width:width);block_seal<=0;ret<=HEADER;pos<=0;body_at<=0;state<=BLOCK;end
    end else ask(at+loaded,LOADED);
    LOADED:if((kind==0&&value[63:15]!=0)||(kind==1&&value[63:8]!=0)||((kind==5||kind==6)&&value[63:6]!=0))bad(4);
     else begin lane<=0;state<=STORE;end
    STORE:begin
     crc<=c16(crc,value[7:0]);canonical_length<=canonical_length+1'b1;
     if(mode==0||loaded==0)writemem(2336+loaded*width+lane,value[7:0],STORED);
     else state<=STORED;
    end
    STORED:begin
     value<=value>>8;
     if(lane+1==width)begin loaded<=loaded+1'b1;records<=records+1'b1;state<=LOAD;end
     else begin lane<=lane+1'b1;state<=STORE;end
    end
    COMPARE:if(item==n)begin
     if(kind==0&&shift_pass!=2)begin shift_pass<=shift_pass+1'b1;item<=0;end
     else begin mode<=0;chosen<=0;best_size<=6+n*width;shift_pass<=0;state<=CHOOSE;end
    end else readmem(2336+item*width,CURLO);
    CURLO:if(kind==0)begin low<=mval;readmem(2337+item*2,CURHI);end
     else begin current_word<={8'd0,mval};readmem(2112+at+item,OLDHI);end
    CURHI:begin
     current_word<={mval,low};
     if((shift_pass==1&&item==0)||(shift_pass==2&&item==32))begin masks[shift_pass][item]<=1;differences[shift_pass]<=differences[shift_pass]+1'b1;item<=item+1'b1;state<=COMPARE;end
     else readmem(2*(at+item)+(shift_pass==1?-2:shift_pass==2?2:0),OLDLO);
    end
    OLDLO:begin low<=mval;readmem(addr+1,OLDHI);end
    OLDHI:begin
     if(current_word!=(kind==0?{mval,low}:{8'd0,mval}))begin masks[shift_pass][item]<=1;differences[shift_pass]<=differences[shift_pass]+1'b1;end
     item<=item+1'b1;state<=COMPARE;
    end
    CHOOSE:begin
     if(6+(kind==0?5+(shift_pass!=0):4)+differences[shift_pass]*width<best_size)begin
      best_size<=6+(kind==0?5+(shift_pass!=0):4)+differences[shift_pass]*width;chosen<=shift_pass;mode<=kind==0&&shift_pass!=0?4:3;
     end
     if(kind==1||shift_pass==2)begin body_at<=0;state<=COPY;end else shift_pass<=shift_pass+1'b1;
    end
    COPY:if(body_at==n*width)begin
     block_length<=mode==0?6+n*width:6+(kind==0?5+(mode==4):4)+differences[chosen]*width;
     body_count<=n*width;block_seal<=0;ret<=HEADER;pos<=0;body_at<=0;state<=BLOCK;
    end else readmem(2336+body_at,COPYREAD);
    COPYREAD:writemem((kind==0?at*2:2112+at)+body_at,mval,COPYNEXT);
    COPYNEXT:begin body_at<=body_at+1'b1;state<=COPY;end
    HEADER:begin
     case(pos)0:emitbyte({5'd0,kind},BODYNEXT);1:emitbyte({5'd0,mode},BODYNEXT);2:emitbyte(at[7:0],BODYNEXT);
      3:emitbyte(at[15:8],BODYNEXT);4:emitbyte(n[7:0],BODYNEXT);5:emitbyte(n[15:8],BODYNEXT);endcase
    end
    BODYNEXT:if(pos<5)begin pos<=pos+1'b1;state<=HEADER;end else begin pos<=0;state<=mode>=3?PREFIX:BODY;end
    PREFIX:begin
     if(mode==4&&pos==0)emitbyte(chosen==1?8'hff:8'h01,NEXTBLOCK);
     else emitbyte(masks[chosen]>>((pos-(mode==4))*8),NEXTBLOCK);
    end
    NEXTBLOCK:if(pos+1==(kind==0?5+(mode==4):4))begin pos<=0;state<=BODY;end else begin pos<=pos+1'b1;state<=PREFIX;end
    BODY:if(body_at==body_count)begin at<=at+n;state<=SECTION;end
     else if(mode>=3&&!masks[chosen][kind==0?body_at>>1:body_at])body_at<=body_at+1'b1;
     else readmem(2336+body_at,BODYREAD);
    BODYREAD:emitbyte(mval,BODYADV);
    BODYADV:begin body_at<=body_at+1'b1;state<=BODY;end
    PREPARE:if(ack_valid)begin
     if(!ack_accept||ack_generation!=generation)bad(5);
     else begin control_kind<=3;control_index<=0;block_length<=8;block_seal<=1;ret<=CONTROL;state<=BLOCK;end
    end
    COMMITWAIT:if(packet_sent)begin valid_base<=1;old_count<=counts[0];serial<=serial+1'b1;release_frame<=1;state<=DRAIN;end
    DRAIN:if(!frame_owned||frame_generation!=generation)state<=IDLE;
    STOPPED:if(!enable)state<=DRAIN;
    default:bad(6);
   endcase
  end
 end
endmodule

module nes_packet589(
 input wire clk,reset,input wire block_valid,output wire block_ready,input wire [8:0] block_length,input wire block_seal,
 input wire byte_valid,output wire byte_ready,input wire [7:0] byte_data,
 output wire tx_valid,input wire tx_ready,output wire [68:0] tx_data,output wire packet_sent,output reg fault
);
 localparam IDLE=0,DATA=1,SEND=2,DONE=3;
 reg [1:0] state,back;reg [63:0] held;reg [3:0] count;
 reg [8:0] used,left;reg last,seal;
 assign block_ready=state==IDLE&&block_length!=0&&block_length<=254&&used+block_length<=254;
 assign byte_ready=state==DATA&&count<8;
 assign tx_valid=state==SEND&&!reset;
 assign tx_data={last,count,held};
 assign packet_sent=tx_valid&&tx_ready&&last;
 always @(posedge clk)begin
  if(reset)begin state<=IDLE;back<=0;held<=0;count<=0;used<=0;left<=0;last<=0;seal<=0;fault<=0;end
  else case(state)
   IDLE:if(block_valid)begin
    if(!block_length||block_length>254)fault<=1;
    else if(used+block_length>254)begin last<=1;back<=IDLE;state<=SEND;end
    else begin left<=block_length;seal<=block_seal;state<=DATA;end
   end
   DATA:if(count==8)begin last<=0;back<=DATA;state<=SEND;end
    else if(byte_valid)begin held[count*8+:8]<=byte_data;count<=count+1'b1;used<=used+1'b1;left<=left-1'b1;if(left==1)state<=DONE;end
   DONE:if(seal)begin last<=1;back<=IDLE;state<=SEND;end else state<=IDLE;
   SEND:if(tx_ready)begin state<=back;count<=0;held<=0;if(last)used<=0;end
  endcase
 end
endmodule
