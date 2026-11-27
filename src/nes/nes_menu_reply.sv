// One request in flight. The SNES and the decoded SPI strobes use host_clk.
// SPI 7A query returns the request and its complement. A reply echoes both,
// followed by result and complement, and commits at the end of the transfer.
module nes_menu_reply(
 input wire clk, reset, cancel, submit, spi_idle, spi_byte, selected,
 input wire [7:0] request_data, incoming,
 input wire [4:0] byte_count, input wire [2:0] bit_count,
 output wire [7:0] pending, output wire [7:0] status
);
 reg [7:0] request;
 reg cancelled,matched,complete;
 // Stop is sampled by one host register. Mask both public views on that
 // edge, then clear the stored transaction before admitting another one.
 always @(posedge clk or posedge reset)
  if(reset)cancelled<=1;else cancelled<=cancel;
 assign pending=cancelled ? 8'd0 : request;
 reg [1:0] result, candidate;
 wire [7:0] result_byte={6'b0,candidate};
 assign status=cancelled ? 8'd0 : {|request,5'b0,result};
 always @(posedge clk or posedge reset) begin
  if(reset) begin
   request<=0;result<=0;candidate<=0;matched<=0;complete<=0;
  end else if(cancelled) begin
   request<=0;result<=0;matched<=0;complete<=0;
  end else begin
   if(submit && request==0 && request_data!=0)begin
    request<=request_data;result<=0;
   end
   if(spi_idle)begin
    if(complete && selected && byte_count==5 && bit_count==0)begin
     request<=0;result<=candidate;
    end
    complete<=0;matched<=0;
   end else if(spi_byte && selected)case(byte_count)
    1: matched<=request!=0 && incoming==request;
    2: matched<=matched && incoming==~request;
    3: begin
     candidate<=incoming[1:0];
     matched<=matched && incoming>=1 && incoming<=3;
    end
    4: complete<=matched && incoming==~result_byte;
    default: complete<=0;
   endcase
  end
 end
endmodule
