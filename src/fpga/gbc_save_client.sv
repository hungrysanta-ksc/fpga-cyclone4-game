// Convert cartridge-RAM CPU accesses and continuous DMA reads into PSRAM transactions.
// The caller must keep each access asserted long enough for completed on reads.
module gbc_save_client(
 input wire clk,reset,read_access,write_access,input wire[16:0]address,input wire[7:0]write_data,
 output wire[7:0]read_data,output wire busy,output reg completed=0,output reg timing_error=0,
 output wire request_valid,output wire request_write,output wire[16:0]request_addr,
 output wire[7:0]request_data,input wire request_ready,response_valid,input wire[7:0]response_data
);
 reg access_q=0,pending=0,accepted=0,write_q=0;
 reg[16:0]address_q=0;reg[7:0]data_q=0;
 reg[7:0]read_data_q=8'hff;
 // The double-speed CPU may sample on the edge which captures this response.
 // Forward the already registered PSRAM response, not the asynchronous pins.
 // Only the pending read for the live address may bypass the retained byte.
 assign read_data=(!reset&&response_valid&&pending&&accepted&&!write_q&&
                   read_access&&address==address_q)?response_data:read_data_q;
 wire access=read_access||write_access;
 // Present a new access to arbitration in the same clock in which it is
 // observed.  Registering pending first would leave a one-clock hole in which
 // a lower-priority PSRAM client could start a transaction and exhaust the GBC
 // read window before this request was admitted.
 // OAM/HDMA holds read_access high while changing the byte address.
 // Reuse the retained transaction tag to detect each byte; a held address
 // after completion still produces exactly one request.
 wire access_changed=access&&(!access_q||address!=address_q||write_access!=write_q);
 wire new_access=!reset&&access_changed&&!pending;
 assign busy=pending||new_access;
 assign request_valid=(pending&&!accepted)||new_access;
 assign request_write=new_access?write_access:write_q;
 assign request_addr=new_access?address:address_q;
 assign request_data=new_access?write_data:data_q;
 always @(posedge clk)begin
  completed<=0;access_q<=access;
  if(reset)begin
   access_q<=0;pending<=0;accepted<=0;write_q<=0;address_q<=0;data_q<=0;
   read_data_q<=8'hff;completed<=0;timing_error<=0;
  end else begin
   if(access_changed)begin
    if(pending)timing_error<=1;
    else begin
     pending<=1;accepted<=0;write_q<=write_access;address_q<=address;data_q<=write_data;
    end
   end
   if(request_valid&&request_ready)accepted<=1;
   if(response_valid&&pending&&accepted)begin
    if(!write_q)read_data_q<=response_data;
    pending<=0;accepted<=0;completed<=1;
    if(!write_q&&!read_access)timing_error<=1;
   end
  end
 end
endmodule
