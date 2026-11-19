// Read-only host-clock observer. No output is connected to a console pin.
module nes_frame862(input wire clk,reset,active,head,show,ack,e0_end,
 input wire beat,input wire [7:0] port_id,input wire [15:0] source,
 input wire [5:0] read_byte, input wire [15:0] generation,
 output wire [7:0] reply);
 reg [23:0] counter;
 reg [5:0] seen;
 reg opened,shown,acked,returned;
 reg follow;
 reg [2:0] follow_kind;
 reg [15:0] follow_time;
 reg [1:0] gaps;
 reg [15:0] before_gap,after_gap;
 reg [5:0] gap_types;
 wire [2:0] kind=port_id==8'h22 ? 4 : port_id==8'h04 ? 5 :
      !source[14] ? 0 : !source[13] ? (source[12] ? 2 : 1) : 3;
 wire valid_port=port_id==8'h18 || port_id==8'h19 || port_id==8'h22 || port_id==8'h04;
 wire transfer=opened && !shown && beat && valid_port;
 wire first_byte=transfer && !seen[kind];
 wire new_head=head && (!opened || acked);
 wire [15:0] now=counter[23:8];
 // 10 coarse ticks separate active-display intervals. A complete VBlank is
 // under 4 ms; adjacent VBlank DMA windows are over 12 ms apart (NTSC).
 wire [7:0] quiet_ticks=now[15:8]-follow_time[15:8];
 wire [3:0] pair_addr=4+{kind,1'b0};
 // Consecutive bytes are at least eight console master clocks apart.
 // Duplicate the first timestamp into the last slot even for a one-byte DMA.
 wire publish=show && !shown && opened;
 wire final_ack=ack && !acked && opened;
 wire write_en=new_head || transfer || follow || publish || final_ack || e0_end && acked;
 wire [3:0] wr_addr=new_head ? 0 : follow ? (5+{follow_kind,1'b0}) :
    transfer ? (first_byte ? pair_addr : pair_addr+1'b1) : publish ? 1 : final_ack ? 2 : 3;
 (* ramstyle="M9K" *) reg [15:0] stamp[0:15];
 reg [15:0] q;
 always @(posedge clk)begin
   if(write_en && active && !reset)stamp[wr_addr]<=follow ? follow_time : now;
   q<=stamp[read_byte[4:1]];
 end
 // SPI byte 1..6 is the header, 7..38 is the little-endian timestamp array.
 // read_byte is byte_count-7, including wraparound for the six header bytes.
 assign reply=read_byte==58 ? 8'h86 : read_byte==59 ? 8'h21 :
    read_byte==60 ? {4'd0,returned,acked,shown,opened} :
    read_byte==61 ? {gaps,seen} : read_byte==62 ? generation[7:0] :
    read_byte==63 ? generation[15:8] :
    read_byte==32 ? before_gap[7:0] : read_byte==33 ? before_gap[15:8] :
    read_byte==34 ? after_gap[7:0] : read_byte==35 ? after_gap[15:8] :
    read_byte==36 ? {2'd0,gap_types} : read_byte[0] ? q[15:8] : q[7:0];
 always @(posedge clk)begin
   counter<=counter+1'b1;
   follow<=first_byte;
   if(transfer)begin
     follow_kind<=kind;follow_time<=now;
     if((|seen) && quiet_ticks>=10)begin
       if(gaps==0)begin before_gap<=follow_time;after_gap<=now;gap_types<={follow_kind,kind};end
       if(gaps!=3)gaps<=gaps+1'b1;
     end
   end
   if(reset || !active)begin
     opened<=0;shown<=0;acked<=0;returned<=0;seen<=0;follow<=0;gaps<=0;
     if(reset)counter<=0;
   end else if(new_head)begin
     opened<=1;shown<=0;acked<=0;returned<=0;seen<=0;gaps<=0;
   end else if(opened)begin
     if(transfer)seen[kind]<=1;
     if(show)shown<=1;
     if(ack)acked<=1;
     if(e0_end && acked)returned<=1;
   end
 end
endmodule
