// Polled Mode-0 endpoint on the NES clock. During a paused file operation the
// ARM uses <=1 MHz SCK. All effects commit at the end of an exact CRC8 frame.
// Request: 59 op index_hi index_lo d0..d7 crc. Reply: idle flags index_hi
// index_lo d0..d7 crc (CRC starts with 59). Index is a 64-bit word or SRAM byte.
module nes_checkpoint_spi #(parameter BOOT_HOLD=0)(
 input wire clk,reset,ss,sck,mosi,paused,sleeping,restored,drained,
 output wire selected,miso, output reg hold_core,save,load, output reg boot_hold,
 input wire stream_ena,stream_rnw,input wire [25:0] stream_addr,input wire [63:0] stream_write,
 input wire [7:0] stream_be,output reg stream_done,output wire [63:0] stream_read,
 output reg bat_read,bat_write,output reg [12:0] bat_addr,output reg [7:0] bat_data,
 input wire bat_valid,input wire [7:0] bat_q
);
 localparam BASE=26'd58720256, WORDS=2658;
 localparam PAUSE=1, RESUME=2, CAPTURE=3, RESTORE=4, WORD_ACK=5, WORD_DATA=6, BAT_RD=7, BAT_WR=8;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] cs,sk,di;
 reg last_sk;
 reg [2:0] bit_no;
 reg [3:0] count;
 reg ours,too_long,checksum_ok,tx_bit;
 reg [7:0] rx_byte,op,rx_crc,tx_crc;
 reg [15:0] index;
 // The walker holds its aligned address and registered data through stream_done.
 wire [15:0] file_index={4'd0,stream_addr[12:1]};
 // The producer word is frozen from its request until a matching ACK.
 // Snapshot the status flags, not a second copy of this word. A new word
 // arriving after the snapshot is invisible for the entire reply.
 reg [63:0] incoming_word;
 reg [7:0] reply_battery;
 assign stream_read=incoming_word;
 reg echo_ok;
 reg pending,reading,fault,operation,restore_op,finished,saw_sleep;
 reg [7:0] battery_reply;reg battery_available;
 wire [7:0] in_byte={rx_byte[6:0],di[1]};
 wire permitted=hold_core && (paused || boot_hold) && drained && !fault;
 reg [7:0] reply_flags;
 wire [15:0] reply_index=reply_flags[2] ? file_index : {3'b0,bat_addr};
 wire [2:0] payload_lane=count[2:0] ^ 3'd4;
 wire masked_lane=!payload_lane[2] && stream_be==8'hf0;
 wire [7:0] file_byte=(reading || masked_lane)?8'd0:stream_write[payload_lane*8+:8];
 wire [7:0] tx_byte=count==1?reply_flags:count==2?reply_index[15:8]:count==3?reply_index[7:0]:
                     count==12?tx_crc:reply_flags[2]?file_byte:
                     count==4?reply_battery:8'd0;
 function automatic [7:0] step_crc(input [7:0] crc,input data_bit);
  return {crc[6:0],1'b0} ^ ((crc[7]^data_bit) ? 8'h07 : 8'h00);
 endfunction
 // CRC8 of the command byte with initial remainder zero.
 function automatic [7:0] command_crc(input [7:0] value);
  reg [7:0] crc;
  crc=0;
  for(int bit_index=7;bit_index>=0;bit_index--)crc=step_crc(crc,value[bit_index]);
  return crc;
 endfunction
 assign selected=!reset && !ss && !cs[1] && ours;
 assign miso=tx_bit;
 always @(posedge clk or posedge reset)begin
  if(reset)begin cs<=3;sk<=0;di<=0;end
  else begin cs<={cs[0],ss};sk<={sk[0],sck};di<={di[0],mosi};end
 end
 always @(posedge clk)begin
  if(reset)begin
   count<=0;bit_no<=0;ours<=0;last_sk<=0;too_long<=0;checksum_ok<=0;tx_bit<=0;
   pending<=0;reading<=0;fault<=0;operation<=0;finished<=0;saw_sleep<=0;restore_op<=0;
   save<=0;load<=0;hold_core<=BOOT_HOLD;boot_hold<=BOOT_HOLD;stream_done<=0;bat_read<=0;bat_write<=0;
   bat_addr<=0;bat_data<=0;battery_available<=0;battery_reply<=0;
   index<=0;rx_byte<=0;op<=0;rx_crc<=0;tx_crc<=0;
   incoming_word<=0;reply_battery<=0;echo_ok<=0;reply_flags<=0;
  end else begin
   last_sk<=sk[1];save<=0;load<=0;stream_done<=0;bat_read<=0;bat_write<=0;
   if(bat_valid)begin battery_available<=1;battery_reply<=bat_q;end
   if(operation && sleeping)saw_sleep<=1;
   if(operation && saw_sleep && !sleeping)begin
    if(pending || (restore_op && !finished && !restored))fault<=1;
    else finished<=1;
    operation<=0;
   end
   if(operation && restored && restore_op)finished<=1;
   if(stream_ena)begin
    if(!permitted || !operation || pending || stream_rnw!=restore_op || stream_addr<BASE || stream_addr>=BASE+2*WORDS ||
       stream_addr[0] || (!stream_rnw && stream_be!=8'hff && !(stream_addr==BASE && stream_be==8'hf0))) fault<=1;
    else begin pending<=1;reading<=stream_rnw;end
   end
   if(cs[1])begin
    if(ours && count==13 && bit_no==0 && !too_long && checksum_ok)case(op)
     // A cold slot load must let the core enter its real paused state.
     // Keep captures inhibited throughout the reset-to-pause handoff.
     PAUSE:begin hold_core<=1;boot_hold<=0;end
     RESUME:if(permitted && !operation && !pending && !sleeping)begin hold_core<=0;boot_hold<=0;end
     CAPTURE,RESTORE:if(permitted && !boot_hold && !operation && !pending && !sleeping)begin
      save<=op==CAPTURE;load<=op==RESTORE;operation<=1;finished<=0;saw_sleep<=0;
      restore_op<=op==RESTORE;battery_available<=0;
     end
     WORD_ACK,WORD_DATA:if(permitted && pending && index==file_index && (op==WORD_DATA)==reading)begin
      if(reply_flags[2] && (reading || echo_ok))begin
       // Only mode 00 is wired on the FF3 board. Quarantine a foreign CPU
       // word while paused, before a valid CRC can commit it to the core.
       if(reading && index==1 && incoming_word[49:48]!=0)fault<=1;
       else begin pending<=0;stream_done<=1;end
      end
     end
     BAT_RD,BAT_WR:if(permitted && !operation && !sleeping && index<8192)begin
      bat_addr<=index[12:0];bat_data<=incoming_word[7:0];bat_read<=op==BAT_RD;bat_write<=op==BAT_WR;battery_available<=0;
     end
    endcase
    count<=0;bit_no<=0;ours<=0;too_long<=0;checksum_ok<=0;tx_bit<=0;
   end else if(sk[1] && !last_sk)begin
    rx_byte<=in_byte;bit_no<=bit_no+1'b1;
    if(count>0 && count<12)begin
     rx_crc<=step_crc(rx_crc,di[1]);
     tx_crc<=step_crc(tx_crc,tx_bit);
    end
    if(count==13)too_long<=1;
    if(&bit_no)begin
     if(count<13)count<=count+1'b1;
     if(!count)begin
      ours<=in_byte==8'h59;rx_crc<=command_crc(8'h59);tx_crc<=command_crc(8'h59);echo_ok<=1;
      reply_flags<={fault,battery_available,finished,operation,reading,pending,permitted,hold_core};
      reply_battery<=battery_reply;
     end else if(count<12)begin
      case(count)
       1:op<=in_byte;2:index[15:8]<=in_byte;3:index[7:0]<=in_byte;
       default:begin
        if(in_byte!=tx_byte)echo_ok<=0;
        incoming_word<={in_byte,incoming_word[63:8]};
       end
      endcase
     end else if(count==12)checksum_ok<=in_byte==rx_crc;
    end
   end else if(!sk[1] && last_sk && ours && count!=0 && count<=12)
    tx_bit<=tx_byte[7-bit_no];
  end
 end
endmodule
