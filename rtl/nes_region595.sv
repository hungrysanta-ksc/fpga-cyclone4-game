// SPDX-License-Identifier: MIT
// One sealed dual-clock page. The NES side cannot write it again until POP.
module nes_region595(input wire clk,host_clk,reset,enable,frame_owned,geometry_valid,
 input wire [15:0] generation,input wire [31:0] epoch,
 input wire [5:0] groups,palettes,input wire [7:0] objects,exceptions,rows,input wire [2:0] patches,
 output wire query,output wire [2:0] query_kind,output wire [12:0] query_index,output wire [15:0] query_generation,
 input wire response,hit,input wire [63:0] data,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,output wire selected,miso,
 output reg release_frame,output reg [3:0] source_fault,output wire host_fault,packet_fault);
 function automatic [15:0] crc16(input [15:0] c,input [7:0] b);
  integer i;reg [15:0] t;begin t=c^{b,8'b0};for(i=0;i<8;i=i+1)t=t[15]?(t<<1)^16'h1021:t<<1;crc16=t;end
 endfunction
 function automatic [31:0] crc32(input [31:0] c,input [7:0] b);
  integer i;reg [31:0] t;begin t=c^b;for(i=0;i<8;i=i+1)t=t[0]?(t>>1)^32'hedb88320:t>>1;crc32=t;end
 endfunction
 function automatic [63:0] raster_next(input [63:0] v);
  reg [14:0] lo;begin lo=v[14:0];
   if(lo[14:12]!=7)lo[14:12]=lo[14:12]+1'b1;
   else begin lo[14:12]=0;case(lo[9:5])29:begin lo[9:5]=0;lo[11]=!lo[11];end 31:lo[9:5]=0;default:lo[9:5]=lo[9:5]+1'b1;endcase end
   raster_next={v[63:15],lo};end
 endfunction

 localparam HELLO=0,HDR=1,SCAN=2,ASK=3,WAITQ=4,VALUE=5,SUMMARY=6,MAP_END=7,
  REQUEST=8,ROW=9,ROW_HEADER=10,ROW_END=11,DECIDE=12,NONMAP=13,BLOCK_HEAD=14,
  END_META=15,END_RAW=16,PREPARE=17,COMMIT=18,RAW_BEGIN=19,LEASE_END=20,
  PREFIX=21,SEND=22,POP=23,FAULT=24;
 reg [4:0] state,after_pop;
 reg [2:0] phase,kind;
 reg [7:0] ordinal,addr,length,pos,chunk,left;
 reg [15:0] gen,token,records,bytes_count,map_crc,stream_crc,first_word,last_word;
 reg [31:0] serial,owned_epoch,mask,digest,watchdog;
 reg warm,base_valid,repaired,action_toggle;
 reg [5:0] row,word_at,row_total;
 reg [12:0] cursor,row_base,limit;
 reg [3:0] lane,width;
 reg [63:0] value,first,previous;
 reg equal_run,linear_run;
 reg [7:0] used_rows;
 wire [31:0] all_rows=32'hffffffff>>(32-row_total);
 (* async_reg="true" *) reg [1:0] spi_fault_sync;
 always @(posedge clk or posedge reset)
  if(reset)spi_fault_sync<=0;else spi_fault_sync<={spi_fault_sync[0],host_fault};
 wire live=!spi_fault_sync[1]&&!reset && enable && frame_owned && geometry_valid && generation==gen && owned_epoch==epoch;
 assign query=state==ASK && live;
 assign query_index=kind==0 ? row_base+word_at : cursor;
 assign query_kind=kind==6 ? 7 : kind;
 assign query_generation=gen;
 assign packet_fault=0;

 wire event_valid,event_ready,host_event,host_ready;
 wire [134:0] event_word,host_word; // action[6:0],epoch,serial,gen,token,bitmap
 wire [6:0] action=event_word[134:128];
 wire [31:0] request_mask=event_word[31:0];
 wire id_ok=event_word[127:96]==epoch && event_word[95:64]==serial+1'b1;
 wire bound=id_ok && event_word[63:48]==gen && event_word[47:32]==token-1'b1;
 assign event_ready=1;
 nes_native_mailbox165 #(.WIDTH(135)) commands(.src_clk(host_clk),.dst_clk(clk),.reset(reset),
  .src_valid(host_event),.src_ready(host_ready),.src_data(host_word),.dst_valid(event_valid),.dst_ready(event_ready),.dst_data(event_word));
 wire seal_ready,host_seal;wire [9:0] seal_info;
 nes_native_mailbox165 #(.WIDTH(10)) seals(.src_clk(clk),.dst_clk(host_clk),.reset(reset),
  .src_valid(state==SEND && live),.src_ready(seal_ready),.src_data({after_pop==PREPARE,length,1'b0}),
  .dst_valid(host_seal),.dst_ready(1'b1),.dst_data(seal_info));
 wire [7:0] host_addr;reg [7:0] host_byte;
 (* ramstyle="M9K" *) reg [7:0] page[0:255];
 reg write_en;reg [7:0] write_addr,write_byte;
 always @(posedge clk) if(write_en && live) page[write_addr]<=write_byte;
 always @(posedge host_clk)host_byte<=page[host_addr];
 nes_spi595 spi(.clk(host_clk),.reset(reset),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
  .selected(selected),.miso(miso),.seal(host_seal),.length(seal_info[8:1]),.end_raw(seal_info[9]),
  .page_addr(host_addr),.page_byte(host_byte),.event_valid(host_event),.event_ready(host_ready),.event_data(host_word),
  .toggle_async(action_toggle),.source_fault_async(|source_fault),.fault(host_fault));

 wire [15:0] map_words={10'd0,row_total}*33;
 reg [15:0] field;
 always @*begin
  case(kind)
   1:begin limit=224;width=1;end 2:begin limit=objects;width=7;end
   3:begin limit=exceptions;width=4;end 4:begin limit=224;width=7;end
   5:begin limit={palettes,5'd0};width=1;end default:begin limit={patches,8'd0};width=1;end
  endcase
  field=0;write_en=1;write_addr=addr;write_byte=value[7:0];
  case(state)
   HDR:begin
    case(pos[7:1])
     0:field=16'h591;1:field={7'd0,warm,8'd1};
     2:field=owned_epoch[15:0];3:field=owned_epoch[31:16];
     4:field=serial+1'b1;5:field=(serial+32'd1)>>16;
     6:field=warm?serial[15:0]:0;7:field=warm?serial[31:16]:0;
     8:field=gen;9:field=map_words;10,13:field=224;11:field=objects;12:field=exceptions;
     14:field={palettes,5'd0};15:field=patches;
    endcase
    write_byte=pos[0]?field[15:8]:field[7:0];
   end
   VALUE:write_en=(phase!=0);
   SUMMARY:begin case(pos[2:1])
    0:field=~digest[15:0];1:field=~digest[31:16];2:field=first_word;3:field=last_word;endcase
    write_byte=pos[0]?field[15:8]:field[7:0];end
   MAP_END,ROW_END,END_META,END_RAW,COMMIT:begin case(pos[2:1])
    0:case(state) MAP_END:field=16'h5900;ROW_END:field=16'h5901;END_META:field=16'hf004;END_RAW:field=16'hf001;default:field=16'hf003;endcase
    1:field=state==MAP_END?row_total:state==ROW_END?used_rows:state==COMMIT?gen:bytes_count;
    2:field=(state==MAP_END || state==ROW_END)?map_crc:state==COMMIT?serial+1'b1:records;
    3:field=(state==MAP_END || state==ROW_END)?gen:state==COMMIT?(serial+32'd1)>>16:stream_crc;
   endcase write_byte=pos[0]?field[15:8]:field[7:0];end
   ROW_HEADER:begin case(pos[2:1])0:field=0;1:field=row_base;default:field=33;endcase
    write_byte=pos[0]?field[15:8]:field[7:0];end
   BLOCK_HEAD:begin write_addr=2+pos;case(pos)0:write_byte={3'b0,linear_run?2'd2:equal_run?2'd1:2'd0,kind};
     1:write_byte=chunk;default:write_byte=0;endcase end
   PREFIX:begin write_addr=pos;write_byte=pos==0?phase:ordinal;end
   default:write_en=0;
  endcase
 end
 task seal_page(input [4:0] continuation,input [7:0] size);
  begin length<=size;after_pop<=continuation;pos<=0;state<=PREFIX;end
 endtask
 task bad(input [3:0] code);begin source_fault<=code;base_valid<=0;state<=FAULT;end endtask
 wire [7:0] block_items=limit-cursor<32 ? limit-cursor : 32;
 always @(posedge clk or posedge reset)begin
  if(reset)begin state<=HELLO;source_fault<=0;release_frame<=0;serial<=0;base_valid<=0;
   token<=0;owned_epoch<=0;action_toggle<=0;watchdog<=0;ordinal<=0;end
  else begin
   release_frame<=0;
   if(state!=HELLO && state!=LEASE_END && state!=FAULT)watchdog<=watchdog+1'b1;
   if(state!=HELLO && state!=LEASE_END && state!=FAULT && (!live || watchdog==33554431))bad(1);
   else if(event_valid && !(state==HELLO || state==REQUEST || state==DECIDE || state==POP || state==PREPARE))bad(2);
   else case(state)
    HELLO:if(event_valid)begin
     if(!enable||!frame_owned||!geometry_valid||!epoch||!groups||groups>32||rows!=224||
        !palettes||palettes>2||objects>128||exceptions>128||serial==32'hffffffff||
        !id_ok||action>1||event_word[63:0]!=0||(action==1&&(!base_valid||owned_epoch!=epoch)))bad(3);
     else begin state<=HDR;addr<=2;pos<=0;action_toggle<=~action_toggle;
      gen<=generation;owned_epoch<=epoch;row_total<=groups;warm<=action==1;base_valid<=0;repaired<=0;
      row<=0;row_base<=0;kind<=0;word_at<=0;phase<=0;ordinal<=0;watchdog<=0;
      records<=0;bytes_count<=0;map_crc<=16'hffff;end
    end
    HDR:begin addr<=addr+1'b1;pos<=pos+1'b1;if(pos==31)seal_page(SCAN,34);end
    SCAN:if(row==row_total)begin pos<=0;state<=MAP_END;end
     else begin word_at<=0;digest<=32'hffffffff;state<=ASK;end
    ASK:state<=WAITQ;
    WAITQ:if(response)begin
     if(!hit || (kind==0 && |data[63:15]) || (kind==1 && |data[63:8]) ||
        ((kind==5||kind==6)&& |data[63:6]) || (kind==2&&|data[63:49]) ||
        (kind==3&&|data[63:32]) || (kind==4&&|data[63:53]))bad(4);
     else begin value<=data;lane<=0;state<=VALUE;
      if(kind==0)begin if(word_at==0)first_word<=data[15:0];last_word<=data[15:0];end
      else if(left==chunk)begin first<=data;previous<=data;if(kind==4&&data[63:49]!=0)linear_run<=0;end
      else begin equal_run<=equal_run && data==first;linear_run<=linear_run && data==raster_next(previous);previous<=data;end
     end
    end
    VALUE:begin value<=value>>8;lane<=lane+1'b1;
     if(phase!=1)begin bytes_count<=bytes_count+1'b1;
      if(kind==0)begin map_crc<=crc16(map_crc,value[7:0]);digest<=crc32(digest,value[7:0]);end
      else stream_crc<=crc16(stream_crc,value[7:0]);end
     if(phase!=0)addr<=addr+1'b1;
     if(lane+1==(kind==0?2:width))begin
      if(phase!=1)records<=records+1'b1;
      if(kind==0)begin word_at<=word_at+1'b1;
       if(word_at!=32)state<=ASK;
       else if(phase==0 && warm)begin pos<=0;state<=SUMMARY;end
       else begin row<=row+1'b1;row_base<=row_base+33;state<=phase==0?SCAN:ROW;end
      end else begin cursor<=cursor+1'b1;left<=left-1'b1;
       if(left==1)begin pos<=0;state<=BLOCK_HEAD;end else state<=ASK;end
     end
    end
    SUMMARY:begin pos<=pos+1'b1;addr<=addr+1'b1;if(pos==7)begin row<=row+1'b1;row_base<=row_base+33;
     if(addr>=241)seal_page(SCAN,addr+1'b1);else state<=SCAN;end end
    MAP_END:begin addr<=addr+1'b1;pos<=pos+1'b1;if(pos==7)seal_page(warm?REQUEST:ROW,addr+1'b1);end
    REQUEST,DECIDE:if(event_valid)begin
     if(!bound || (request_mask&~all_rows)!=0)bad(5);
     else if((state==REQUEST&&action==2)||(state==DECIDE&&action==3&&!repaired&&request_mask==all_rows))begin
      if(action==3)repaired<=1;
      mask<=request_mask;row<=0;row_base<=0;used_rows<=0;phase<=1;ordinal<=0;addr<=2;state<=ROW;action_toggle<=~action_toggle;
     end else if(state==DECIDE&&action==4&&!request_mask)begin
      action_toggle<=~action_toggle;kind<=1;cursor<=0;phase<=2;ordinal<=0;stream_crc<=map_crc;state<=NONMAP;
     end else bad(6);
    end
    ROW:if(row==row_total)begin state<=ROW_END;pos<=0;end
     else if(!mask[row[4:0]])begin row<=row+1'b1;row_base<=row_base+33;end
     else if(addr>182)seal_page(ROW,addr);
     else begin used_rows<=used_rows+1'b1;pos<=0;word_at<=0;state<=ROW_HEADER;end
    ROW_HEADER:begin pos<=pos+1'b1;addr<=addr+1'b1;if(pos==5)state<=ASK;end
    ROW_END:begin pos<=pos+1'b1;addr<=addr+1'b1;if(pos==7)seal_page(DECIDE,addr+1'b1);end
    NONMAP:if(cursor==limit)begin
     if(kind==5 || kind==6)begin state<=kind==5?END_META:END_RAW;pos<=0;addr<=2;end
     else begin kind<=kind+1'b1;cursor<=0;end
    end else begin chunk<=block_items;left<=block_items;addr<=5;equal_run<=kind!=1&&kind!=5&&block_items>=(kind==6?10:2);
     linear_run<=kind==4 && block_items>=2;state<=ASK;end
    BLOCK_HEAD:begin pos<=pos+1'b1;if(pos==2)seal_page(NONMAP,(linear_run||equal_run)?5+width:addr);end
    END_META,END_RAW,COMMIT:begin pos<=pos+1'b1;addr<=addr+1'b1;if(pos==7)
     seal_page(state==END_META?RAW_BEGIN:state==END_RAW?PREPARE:LEASE_END,10);end
    PREFIX:if(pos==1)state<=SEND;else pos<=1;
    SEND:if(seal_ready)state<=POP;
    POP:if(event_valid)begin
     if(action!=5 || event_word[47:32]!=token)bad(7);
     else begin token<=token+1'b1;ordinal<=ordinal+1'b1;addr<=2;pos<=0;state<=after_pop;
      if(phase==0 && after_pop==ROW)begin row<=0;row_base<=0;mask<=all_rows;used_rows<=0;phase<=1;ordinal<=0;end
      if(after_pop==LEASE_END)begin base_valid<=1;serial<=serial+1'b1;release_frame<=1;end
     end
    end
    RAW_BEGIN:begin phase<=3;kind<=6;cursor<=0;ordinal<=0;state<=NONMAP;end
    PREPARE:if(event_valid)begin if(action!=6 || event_word[63:48]!=gen)bad(8);
     else begin state<=COMMIT;phase<=4;ordinal<=0;pos<=0;addr<=2;end end
    LEASE_END:if(!frame_owned)state<=HELLO;
    default:state<=FAULT;
   endcase
  end
 end
endmodule
