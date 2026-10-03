// Candidate shared-bus controller: three clocks per read / four per write, one release
// clock between transfers. Timing assumptions are checked by rw_tb, not a
// verified specification for the user's unidentified PSRAM part.
module psram_rw3(input wire clk,reset,req_valid,req_write,
 input wire[22:0]req_addr,input wire[15:0]req_data,
 output wire req_ready,output reg rsp_valid,output reg[15:0]rsp_data,
 output reg[21:0]rom_addr,output wire rom_1ce,rom_2ce,rom_oe,rom_we,
 output wire rom_bhe,rom_ble,inout wire[15:0]rom_data);
 // Local asynchronous assertion, synchronous release for the output gates.
 // Admission waits for this extra startup clock; steady-state cycles are unchanged.
 reg pin_reset;
 always @(posedge clk or posedge reset)begin if(reset)pin_reset<=1;else pin_reset<=0;end
 reg rom_1ce_r,rom_2ce_r,rom_oe_r,rom_we_r;
 assign rom_1ce=pin_reset?1'b1:rom_1ce_r;assign rom_2ce=pin_reset?1'b1:rom_2ce_r;
 assign rom_oe=pin_reset?1'b1:rom_oe_r;assign rom_we=pin_reset?1'b1:rom_we_r;
 reg[2:0]remaining;reg writing,drive;
 reg[15:0]output_data;
 assign req_ready=!reset && !pin_reset && remaining==0;
 assign rom_data=(drive&&!pin_reset)?output_data:16'hzzzz;
 assign rom_bhe=0;assign rom_ble=0;
 always @(posedge clk)rsp_data<={rom_data[7:0],rom_data[15:8]};
 always @(posedge clk)begin
  rsp_valid<=0;
  if(reset||pin_reset)begin remaining<=0;drive<=0;writing<=0;
   rom_1ce_r<=1;rom_2ce_r<=1;rom_oe_r<=1;rom_we_r<=1;rom_addr<=0;output_data<=0;
  end else if(remaining>0)begin
   remaining<=remaining-1;
   if(remaining==2 && writing)rom_we_r<=1; // Three-clock write pulse, then one-clock hold.
   if(remaining==1)begin
    rsp_valid<=1;
    drive<=0;rom_1ce_r<=1;rom_2ce_r<=1;rom_oe_r<=1;rom_we_r<=1;
   end
  end else begin
   // The previous completion edge started the release interval. This edge
   // is one whole clock later, so it may accept the next request.
   if(req_valid&&req_ready)begin
    remaining<=req_write?4:3;writing<=req_write;rom_addr<=req_addr[22:1];
    rom_1ce_r<=req_addr[0];rom_2ce_r<=!req_addr[0];
    rom_oe_r<=req_write;rom_we_r<=!req_write;drive<=req_write;
    output_data<={req_data[7:0],req_data[15:8]};
   end
  end
 end
endmodule
