// Hold one-cycle mcu_cmd read/write pulses until the shared PSRAM transaction
// completes. mcu_request_ready is the completion pulse expected by mcu_cmd.
module mcu_psram_client(
 input wire clk,reset,read_request,write_request,input wire[23:0]address,input wire[7:0]write_data,
 output reg request_ready=0,output reg[7:0]read_data=0,output wire busy,output reg overlap_error=0,
 output wire request_valid,output wire request_write,output wire[23:0]request_addr,
 output wire[7:0]request_data,input wire endpoint_ready,response_valid,input wire[7:0]response_data
);
 reg pending=0,accepted=0,write_q=0;reg[23:0]address_q=0;reg[7:0]data_q=0;
 wire command=read_request||write_request;
 assign busy=pending;assign request_valid=pending&&!accepted;
 assign request_write=write_q;assign request_addr=address_q;assign request_data=data_q;
 always @(posedge clk)begin
  request_ready<=0;
  if(reset)begin pending<=0;accepted<=0;write_q<=0;address_q<=0;data_q<=0;
   request_ready<=0;read_data<=0;overlap_error<=0;
  end else begin
   if(command)begin
    if(pending)overlap_error<=1;
    else begin pending<=1;accepted<=0;write_q<=write_request;address_q<=address;data_q<=write_data;end
   end
   if(request_valid&&endpoint_ready)accepted<=1;
   if(response_valid&&pending&&accepted)begin
    if(!write_q)read_data<=response_data;
    pending<=0;accepted<=0;request_ready<=1;
   end
  end
 end
endmodule
