 // Diagnostic taps are all in the host domain. The low 15 clock bits retain
 // the original offer phase and reset pipeline used by the source transport.
 reg clear_record;
 reg [27:0] clock_count;
 wire [11:0] stamp=clock_count[27:16];
 assign offer_phase=clock_count[14];
 reg [11:0] tile_at,seal_at,show_at,ack_at,move_at;
 reg have_tile,frame_tile,sealed,shown,complete,read_ok,neutral,moved;
 always @(posedge clk) begin
   clear_record<=reset || !active || cancel;
   clock_count<=clear_record ? 28'd0 : clock_count+1'b1;
   if(clear_record) begin
     have_tile<=0;frame_tile<=0;sealed<=0;shown<=0;complete<=0;
     read_ok<=0;neutral<=0;moved<=0;
   end else begin
     if(header && !directions) neutral<=1;
     if(neutral && !moved && |directions) begin moved<=1;move_at<=stamp;end
     if(returned) begin tile_at<=stamp;have_tile<=1;end
     if(header && data==1) begin sealed<=0;shown<=0;end
     if(header && data==3 && !sealed) begin seal_at<=stamp;sealed<=1;end
     if(sealed && !shown && show) begin show_at<=stamp;shown<=1;end
     if(retired && op==3) begin
       ack_at<=stamp;frame_tile<=have_tile;have_tile<=0;complete<=sealed && shown;
     end
     if(query) read_ok<=complete;
     if(header || returned || retired || first_e9) begin
       read_ok<=0;
       if(!(retired && op==3)) complete<=0;
     end
   end
 end
 reg [7:0] out_byte;
 always @(posedge clk) case(index)
   1:out_byte<=8'hd2;
   2:out_byte<=generation[7:0];
   3:out_byte<=generation[15:8];
   4:out_byte<={2'b0,frame_tile,moved,directions};
   5:out_byte<=tile_at[7:0];
   6:out_byte<=seal_at[7:0];
   7:out_byte<=show_at[7:0];
   8:out_byte<=ack_at[7:0];
   9:out_byte<={seal_at[11:8],tile_at[11:8]};
   10:out_byte<={ack_at[11:8],show_at[11:8]};
   11:out_byte<=move_at[7:0];
   12:out_byte<={4'b0,move_at[11:8]};
   15:out_byte<=read_ok && !clear_record ? 8'h5a : 0;
   default:out_byte<=0;
 endcase
 assign reply=out_byte;
endmodule
