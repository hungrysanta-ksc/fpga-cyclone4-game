# SPDX-License-Identifier: MIT
"""Five-entry sequential tag lookup; one synchronous data RAM, no parallel CAM."""
BODY=r'''
 (* ramstyle="M9K, no_rw_check" *) reg [7:0] bytes[0:127];
 reg [17:0] tags[0:4];reg [15:0] valid[0:4];
 reg [2:0] scan,slot,replacement;
 localparam IDLE=0,SCAN=1,HIT=2,MISS=3,WAIT=4,REPLY=5;
 reg [2:0] state;reg [31:0] cached_epoch;
 reg [21:0] held_address;reg [15:0] held_generation;reg [7:0] value,q;reg failed;
 wire invalidate=reset||flush||cached_epoch!=content_epoch;
 wire live=!invalidate;wire pending=state==WAIT;
 wire good=back_response&&!back_error&&back_response_address==held_address&&back_response_generation==held_generation;
 assign ready=live&&state==IDLE&&back_idle;
 assign idle=live&&state==IDLE&&back_idle;
 assign response=live&&state==REPLY;assign error=failed;
 assign response_address=held_address;assign response_generation=held_generation;assign data=value;
 assign back_request=live&&state==MISS;assign back_abort=invalidate;
 assign back_address=held_address;assign back_generation=held_generation;
 always @(posedge clk)begin
  q<=bytes[{scan,held_address[3:0]}];
  if(live&&pending&&good)bytes[{slot,held_address[3:0]}]<=back_data;
 end
 always @(posedge clk)begin
  cached_epoch<=content_epoch;
  if(invalidate)begin
   state<=IDLE;scan<=0;slot<=0;replacement<=0;held_address<=0;held_generation<=0;value<=0;failed<=0;
   for(integer j=0;j<5;j++)begin tags[j]<=0;valid[j]<=0;end
  end else case(state)
   IDLE:if(request&&ready)begin held_address<=address;held_generation<=generation;scan<=0;failed<=0;state<=SCAN;end
   SCAN:begin
    if(valid[scan]!=0&&tags[scan]==held_address[21:4])begin
     slot<=scan;state<=valid[scan][held_address[3:0]]?HIT:MISS;
    end else if(scan==4)begin
     slot<=replacement;tags[replacement]<=held_address[21:4];valid[replacement]<=0;
     replacement<=replacement==4?0:replacement+1'b1;state<=MISS;
    end else scan<=scan+1'b1;
   end
   HIT:begin value<=q;state<=REPLY;end
   MISS:if(back_ready)state<=WAIT;
   WAIT:if(back_response)begin
    value<=back_data;failed<=!good;state<=REPLY;
    if(good)valid[slot]<=valid[slot]|(16'd1<<held_address[3:0]);
   end
   REPLY:state<=IDLE;
   default:begin failed<=1;state<=IDLE;end
  endcase
 end
endmodule
'''
def apply(d):
 p=d/'nes_chr_cache192.sv';s=p.read_text();s=s[:s.index(' reg [7:0] bytes')]+BODY;p.write_text(s,newline='\n')
