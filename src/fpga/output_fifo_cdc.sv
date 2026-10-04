// Four transactions, logic storage only. Ready acknowledges ENQUEUE, not SRAM
// commit. The page owner MUST wait for drained before publishing a frame.
// Both domains must reset together. Gray pointers cross through two flops;
// data is stable before the synchronized write pointer exposes each entry.
module output_fifo_cdc(
 input wire source_clk,bus_clk,reset,
 input wire word_valid,input wire[15:0]word_addr,word_data,output reg word_ready,
 input wire byte_valid,input wire[15:0]byte_addr,input wire[7:0]byte_data,output reg byte_ready,
 output wire write_valid,input wire write_ready,output wire[15:0]write_addr,write_data,
 output wire write_word,output wire drained
);
 (* async_reg="true" *)reg[1:0]source_reset,bus_reset;
 always @(posedge source_clk or posedge reset)
  if(reset)source_reset<=3;else source_reset<={source_reset[0],1'b0};
 always @(posedge bus_clk or posedge reset)
  if(reset)bus_reset<=3;else bus_reset<={bus_reset[0],1'b0};
 (* ramstyle="logic" *)reg[32:0]entries[0:3];
 reg[2:0]write_bin,write_gray,read_bin,read_gray;
 (* async_reg="true" *)reg[2:0]read_sync0,read_sync1,write_sync0,write_sync1;
 reg[1:0]cooldown;
 wire full=write_gray=={~read_sync1[2:1],read_sync1[0]};
 wire empty=read_gray==write_sync1;
 wire[2:0]next_write=write_bin+1'b1,next_read=read_bin+1'b1;
 assign drained=read_sync1==write_gray&&!source_reset[1];
 assign write_valid=!empty&&!bus_reset[1];
 assign {write_word,write_addr,write_data}=entries[read_bin[1:0]];
 always @(posedge source_clk or posedge source_reset[1])begin
  if(source_reset[1])begin
   write_bin<=0;write_gray<=0;read_sync0<=0;read_sync1<=0;
   word_ready<=0;byte_ready<=0;cooldown<=0;
  end else begin
   read_sync0<=read_gray;read_sync1<=read_sync0;
   word_ready<=0;byte_ready<=0;
   if(cooldown!=0)cooldown<=cooldown-1'b1;
   else if(!full&&(byte_valid||word_valid))begin
    entries[write_bin[1:0]]<={!byte_valid,byte_valid?byte_addr:word_addr,
                               byte_valid?{8'b0,byte_data}:word_data};
    write_bin<=next_write;write_gray<=(next_write>>1)^next_write;
    word_ready<=!byte_valid;byte_ready<=byte_valid;cooldown<=2;
   end
  end
 end
 always @(posedge bus_clk or posedge bus_reset[1])begin
  if(bus_reset[1])begin read_bin<=0;read_gray<=0;write_sync0<=0;write_sync1<=0;end
  else begin
   write_sync0<=write_gray;write_sync1<=write_sync0;
   if(write_valid&&write_ready)begin read_bin<=next_read;read_gray<=(next_read>>1)^next_read;end
  end
 end
endmodule
