// Boot-only MCU byte endpoint for the physical 512 KiB SRAM.
// Firmware holds SNES reset and RUN=0. Completion follows WE deassertion and
// data/address hold; RUN=1 refuses further boot writes without touching pins.
module gbc_sram_loader(
 input wire clk,bus_clk,run,read_request,write_request,
 input wire[18:0]address,input wire[7:0]write_data,
 output reg done,output reg[7:0]read_data,output wire run_active,
 output reg[18:0]ram_addr,output reg ram_oe,ram_we,
 inout wire[7:0]ram_data
);
 initial begin done=0;read_data=0;ram_addr=0;ram_oe=1;ram_we=1;end
 reg request_toggle=0,ack_toggle=0,request_seen=0,ack_seen=0;
 reg[18:0]address_q=0;reg[7:0]write_q=0,result_q=0;reg is_write=0;
 (* async_reg="true" *)reg[1:0]request_sync=0,ack_sync=0,run_sync=0;
 assign run_active=run_sync[1];
 always @(posedge clk)begin
  done<=0;ack_sync<={ack_sync[0],ack_toggle};
  if(read_request||write_request)begin
   address_q<=address;write_q<=write_data;is_write<=write_request;
   request_toggle<=!request_toggle;
  end
  if(ack_sync[1]!=ack_seen)begin
   ack_seen<=ack_sync[1];read_data<=result_q;done<=1;
  end
 end
 reg[3:0]state=0;
 reg writing=0,drive=0;reg[7:0]data_q=0;
 assign ram_data=drive?data_q:8'hzz;
 always @(posedge bus_clk)begin
  request_sync<={request_sync[0],request_toggle};run_sync<={run_sync[0],run};
  case(state)
   0:if(request_sync[1]!=request_seen)begin
    request_seen<=request_sync[1];
    if(run_active)begin ack_toggle<=request_sync[1];result_q<=8'hff;end
    else begin
     ram_addr<=address_q;data_q<=write_q;writing<=is_write;
     drive<=is_write;state<=1;
    end
   end
   2:begin ram_we<=!writing;ram_oe<=writing;state<=3;end
   6:begin
    if(!writing)result_q<=ram_data;
    ram_we<=1;ram_oe<=1;state<=7;
   end
   8:begin drive<=0;state<=9;end
   9:begin ack_toggle<=request_seen;state<=0;end
   default:state<=state+1'b1;
  endcase
 end
endmodule
