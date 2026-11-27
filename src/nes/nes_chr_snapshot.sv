// FF3 uses the upper 8 KiB of the renderer SRAM while the NES profile owns it.
// The live PPU never waits for a display reader. Only a clean, complete copy
// can be leased. A write during visible capture rejects that capture.
module nes_chr_snapshot (
 input wire clk, reset, changed, start, collecting, discard, retire,
 input wire [15:0] start_gen, retire_gen,
 output wire can_start, output reg conflict,
 output reg [12:0] scan_addr, input wire [7:0] scan_data,
 input wire read_req, cancel, input wire [17:0] read_addr,
 input wire [15:0] read_gen, output wire ready, idle,
 output reg response, error, output reg [7:0] data,
 output reg [17:0] reply_addr, output reg [15:0] reply_gen,
 output wire [18:0] ram_addr, output wire oe_n,we_n,
 input wire [7:0] ram_q, output wire drive_data, output reg [7:0] write_data
);
 localparam FETCH=0, SETUP=1, WRITE=2, HOLD=3, CLEAN=4,
            READ1=5, READ2=6, SAMPLE=7, LEAD=8;
 reg [3:0] state;
 reg held, dirty;
 reg [15:0] owner;
 reg [12:0] bus_addr;
 assign ram_addr={6'h3f,bus_addr};
 assign oe_n=reset || (state!=READ1 && state!=READ2 && state!=SAMPLE);
 assign we_n=reset || state!=WRITE;
 assign drive_data=!reset && (state==LEAD || state==WRITE || state==HOLD);
 assign can_start=!reset && !held && state==CLEAN && !dirty && !changed;
 assign idle=state!=READ1 && state!=READ2 && state!=SAMPLE && !response;
 assign ready=!reset && !cancel && held && state==CLEAN && !response;
 always @(posedge clk) begin
  if(reset) begin
   held<=0;dirty<=0;conflict<=0;scan_addr<=0;bus_addr<=0;write_data<=0;
   owner<=0;state<=FETCH;response<=0;error<=0;reply_addr<=0;reply_gen<=0;data<=0;
  end else begin
   response<=0;error<=0;
   if(changed)begin
    dirty<=1;
    if(held && collecting) conflict<=1;
   end
   if(start && can_start)begin held<=1;owner<=start_gen;conflict<=0;end
   if(discard || (retire && retire_gen==owner))begin held<=0;conflict<=0;end
   case(state)
    FETCH:state<=SETUP;
    SETUP:begin write_data<=scan_data;bus_addr<=scan_addr;state<=LEAD;end
    LEAD:state<=WRITE;
    WRITE:state<=HOLD;
    HOLD:begin
     if(&scan_addr)begin
      scan_addr<=0;dirty<=0;
      state<=(dirty||changed)?FETCH:CLEAN;
     end else begin scan_addr<=scan_addr+1'b1;state<=FETCH;end
    end
    CLEAN:begin
     if(!held && (dirty||changed))begin scan_addr<=0;dirty<=0;state<=FETCH;end
     else if(read_req && ready)begin
      reply_addr<=read_addr;reply_gen<=read_gen;bus_addr<=read_addr[12:0];
      if(read_gen!=owner || |read_addr[17:13])begin error<=1;response<=1;end
      else state<=READ1;
     end
    end
    READ1:state<=cancel?CLEAN:READ2;
    READ2:state<=cancel?CLEAN:SAMPLE;
    SAMPLE:begin
     if(!cancel && held)begin data<=ram_q;response<=1;end
     state<=CLEAN;
    end
   endcase
  end
 end
endmodule
