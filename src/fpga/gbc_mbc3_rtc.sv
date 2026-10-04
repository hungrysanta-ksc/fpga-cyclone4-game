// MBC3 RTC. 33,555,556 Hz is the board PLL (8 MHz * 151 / 36).
// 1/16-second phase restart on seconds writes; independent watchdog timebase.
// Integer divider rounding is below 0.2 ppm on this PLL.
// Battery clock survives game reset, menu pause, fast forward and state restore.
module gbc_mbc3_rtc #(parameter SECOND_CYCLES=33555556)(
 input wire clk,reset,run_core,enabled,game_reset,
 input wire latch_write,input wire[7:0]cart_data,
 input wire rtc_write,input wire[3:0]rtc_select,output reg[7:0]cart_read,
 input wire host_safe,mcu_read,mcu_write,input wire[3:0]mcu_addr,input wire[7:0]mcu_data,
 output reg mcu_done,output reg[7:0]mcu_result,
 input wire state_commit,input wire[63:0]state_data,output wire[28:0]state_bits,
 output wire dirty,watchdog_tick
);
 reg[5:0]seconds,minutes;reg[4:0]hours;reg[8:0]days;reg halted,carry;
 reg[27:0]latched;reg latch_zero;reg[21:0]divider;reg[3:0]fraction;
 localparam QUANTUM_CYCLES=SECOND_CYCLES/16;
 wire[27:0]live={carry,halted,days,hours,minutes,seconds};
 wire host_write=mcu_write&&!run_core;
 assign state_bits={latched,latch_zero};
 assign dirty=enabled&&rtc_write;
 // Free-running 1/16-second pulse shared by bounded capture watchdogs.
 assign watchdog_tick=divider==QUANTUM_CYCLES-1;
 function[7:0]read_byte(input[27:0]v,input[3:0]a);
 begin case(a)
 0:read_byte={2'b0,v[5:0]};1:read_byte={2'b0,v[11:6]};
 2:read_byte={3'b0,v[16:12]};3:read_byte=v[24:17];
 4:read_byte={v[27:26],5'b0,v[25]};default:read_byte=8'hff;
 endcase end endfunction
 wire host_read=mcu_read&&host_safe&&mcu_addr[2:0]<5;
 wire[27:0]read_value=host_read&&!mcu_addr[3]?live:latched;
 wire[3:0]read_index=host_read?{1'b0,mcu_addr[2:0]}:{1'b0,rtc_select[2:0]};
 wire[7:0]decoded=read_byte(read_value,read_index);
 wire write_live=host_write&&!mcu_addr[3]||(enabled&&rtc_write);
 wire[2:0]write_index=host_write?mcu_addr[2:0]:rtc_select[2:0];
 wire[7:0]write_value=host_write?mcu_data:cart_data;
 always @* cart_read=enabled?decoded:8'hff;
 always @(posedge clk)begin
  mcu_done<=mcu_read||mcu_write;
  if(mcu_read)mcu_result<=host_read?decoded:8'hff;
  if(reset)begin
   seconds<=0;minutes<=0;hours<=0;days<=0;halted<=0;carry<=0;
   latched<=0;latch_zero<=0;divider<=0;fraction<=0;mcu_done<=0;mcu_result<=0;
  end else begin
   if(game_reset)latch_zero<=0;
   else if(state_commit)latch_zero<=state_data[16];
   else if(enabled&&latch_write)latch_zero<=cart_data==0;
   // Boot import reuses the live write port: stage latched values, copy on E,
   // then install the elapsed-time-adjusted live values while RUN is clear.
   if(host_write&&mcu_addr==14)latched<=live;
   else if(state_commit)latched<=state_data[44:17];
   else if(!game_reset&&enabled&&latch_write&&latch_zero&&cart_data==1)latched<=live;
   if(watchdog_tick)divider<=0;
   else divider<=divider+1'b1;
   if(enabled&&!halted&&watchdog_tick)fraction<=fraction+1'b1;
   if(enabled&&!halted&&watchdog_tick&&(&fraction))begin
    if(seconds==59)begin seconds<=0;
     if(minutes==59)begin minutes<=0;
      if(hours==23)begin hours<=0;days<=days+1'b1;if(&days)carry<=1;end
      else hours<=hours+1'b1;
     end else minutes<=minutes+1'b1;
    end else seconds<=seconds+1'b1;
   end
   if(host_write)fraction<=0;
   if(write_live)case(write_index)
    0:begin seconds<=write_value[5:0];fraction<=0;end
    1:minutes<=write_value[5:0];2:hours<=write_value[4:0];3:days[7:0]<=write_value;
    4:begin days[8]<=write_value[0];halted<=write_value[6];carry<=write_value[7];end
   endcase

  end
 end
endmodule
