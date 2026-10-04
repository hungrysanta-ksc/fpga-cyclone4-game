// Synchronous register endpoint. The physical SNES address/edge decoder must
// qualify write_strobe and meet this clock domain's setup/hold requirements.
// 0 signature C3; 1 command (bit0 upload, bit7 clear local command error);
// 2 status {000,error,snapshot_available,page,display_valid,busy};
// 3/4 completed upload transaction counter (not a source frame counter).
// 5 stages SNES $4218, 6 atomically commits $4219 and toggles joy_update[8].
module snes_upload_regs(
 input wire clk,reset,write_strobe,input wire[3:0]reg_addr,input wire[7:0]write_data,
 output reg[7:0]read_data,output reg upload_start,
 input wire upload_busy,upload_done,upload_page,upload_valid,upload_error,
 output reg[9:0]joy_update
);
 reg pending,available,page,valid,command_error;
 reg[15:0]transactions;
 reg[7:0]pad_low;
 wire busy=pending||upload_busy;
 always @*begin
  case(reg_addr)
   0:read_data=8'hc3;
   2:read_data={3'b0,command_error||upload_error,available&&!busy,page,valid&&available&&!busy,busy};
   3:read_data=transactions[7:0];
   4:read_data=transactions[15:8];
   5:read_data=pad_low;
   6:read_data=joy_update[7:0];
   default:read_data=0;
  endcase
 end
 always @(posedge clk)begin
  if(reset)begin
   pending<=0;available<=0;page<=0;valid<=0;command_error<=0;
   transactions<=0;upload_start<=0;pad_low<=0;joy_update<=0;
  end else begin
   upload_start<=0;
   if(upload_done)begin
    if(!pending)command_error<=1;
    else begin
     pending<=0;available<=1;page<=upload_page;valid<=upload_valid;
     transactions<=transactions+1'b1;
    end
   end
   if(write_strobe&&reg_addr==1)begin
    if(write_data[7])command_error<=0;
    if(write_data[0])begin
     if(busy)command_error<=1;
     else begin pending<=1;available<=0;upload_start<=1;end
    end
   end
   if(write_strobe&&reg_addr==5)pad_low<=write_data;
   if(write_strobe&&reg_addr==6)begin
    // $4218: B,Y,Select,Start,Up,Down,Left,Right; $4219 bit0: A.
    // Ignore Y/X/L/R because the Game Boy has no counterparts.
    joy_update[7:0]<={pad_low[3],pad_low[2],pad_low[0],write_data[0],
                      pad_low[4],pad_low[5],pad_low[6],pad_low[7]};
    joy_update[8]<=write_data[1]; // C37 R hold, prequalified against menu chord
    joy_update[9]<=~joy_update[9];
   end
  end
 end
endmodule
