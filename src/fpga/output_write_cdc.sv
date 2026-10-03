// One outstanding SRAM write crossing. Source ready means COMMITTED, not queued.
// reset must assert in both domains together. Each domain releases synchronously.
// The request bundle remains stable until a synchronized completion returns;
// the receiver waits two synchronizer clocks before sampling it. Board timing
// constraints for these bundled paths are a separate integration requirement.
module output_write_cdc(
 input wire source_clk,bus_clk,reset,
 input wire word_valid,input wire[15:0]word_addr,word_data,output reg word_ready,
 input wire byte_valid,input wire[15:0]byte_addr,input wire[7:0]byte_data,output reg byte_ready,
 output wire write_valid,input wire write_ready,output wire[15:0]write_addr,
 output wire[7:0]write_data
);
 (* async_reg = "true" *) reg[1:0]source_reset,bus_reset;
 always @(posedge source_clk or posedge reset)
  if(reset)source_reset<=3;else source_reset<={source_reset[0],1'b0};
 always @(posedge bus_clk or posedge reset)
  if(reset)bus_reset<=3;else bus_reset<={bus_reset[0],1'b0};
 reg request_toggle,complete_toggle;
 (* async_reg = "true" *) reg[1:0]request_sync,complete_sync;
 always @(posedge source_clk or posedge source_reset[1])
  if(source_reset[1])complete_sync<=0;else complete_sync<={complete_sync[0],complete_toggle};
 always @(posedge bus_clk or posedge bus_reset[1])
  if(bus_reset[1])request_sync<=0;else request_sync<={request_sync[0],request_toggle};
 reg[15:0]held_addr,held_data;reg held_word;
 reg[1:0]source_state;
 always @(posedge source_clk or posedge source_reset[1])begin
  if(source_reset[1])begin source_state<=0;request_toggle<=0;word_ready<=0;byte_ready<=0;
   held_addr<=0;held_data<=0;held_word<=0;end
  else begin
   word_ready<=0;byte_ready<=0;
   case(source_state)
    0:if(byte_valid||word_valid)begin
     held_word<=!byte_valid;held_addr<=byte_valid?byte_addr:word_addr;
     held_data<=byte_valid?{8'b0,byte_data}:word_data;
     request_toggle<=!request_toggle;source_state<=1;
    end
    1:if(complete_sync[1]==request_toggle)begin
     word_ready<=held_word;byte_ready<=!held_word;source_state<=2;
    end
    // The producer observes its completion at this edge and withdraws valid.
    2:source_state<=0;
   endcase
  end
 end
 reg active,high_byte,received_word;
 reg[15:0]received_addr,received_data;
 // bus_reset asserts asynchronously too; using the raw source reset here
 // would bypass the domain synchronizer on the outward bus-valid signal.
 assign write_valid=active&&!bus_reset[1];
 assign write_addr=received_addr+high_byte;
 assign write_data=high_byte?received_data[15:8]:received_data[7:0];
 always @(posedge bus_clk or posedge bus_reset[1])begin
  if(bus_reset[1])begin complete_toggle<=0;active<=0;high_byte<=0;
   received_word<=0;received_addr<=0;received_data<=0;end
  else if(!active)begin
   if(request_sync[1]!=complete_toggle)begin
    received_addr<=held_addr;received_data<=held_data;received_word<=held_word;
    high_byte<=0;active<=1;
   end
  end else if(write_ready)begin
   if(received_word&&!high_byte)high_byte<=1;
   else begin active<=0;complete_toggle<=request_sync[1];end
  end
 end
endmodule
