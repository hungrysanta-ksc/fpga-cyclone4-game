// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module bg659_tb;
 reg clk=0,mem_clk=0,reset=1,read_reset=1,check_enable=0,check_request=0;
 always #23.281 clk=~clk;always #2.976 mem_clk=~mem_clk;
 reg [18:0] check_address;wire check_ready,check_response,check_fault;wire [18:0] check_response_address;wire [7:0]check_data;
 reg load_begin=0,load_valid=0,load_end=0,start=0,stop=0;reg [7:0]load_data;
 wire load_ready,loaded,run_enable,boot_fault;wire[3:0]boot_error;wire [18:0]loaded_bytes;
 wire ready,response,err;wire[21:0] reply,pin_addr;wire[7:0] rom_data;wire[15:0]word_data;
 wire ce1,ce2,oe,we,bhe,ble;wire[15:0]dq;reg [7:0] native_mem[0:393215],ram[0:393215];
 wire [21:0] physical={pin_addr[19:0],!ce2,1'b0};
 wire [18:0] offset={physical[21],physical[17:0]};
 reg [15:0] pins=0;
 // 70 ns asynchronous memory. Cancel a read if its address or enables change.
 always @(offset,ce1,ce2,oe,we) begin
  if(!oe && we && (!ce1!=!ce2))pins<={ram[offset],ram[offset+1]} ;
  else pins<=16'hxxxx;
 end
 wire [15:0] delayed;assign #70 delayed=pins;
 assign dq=(!oe && we)?delayed:16'hzzzz;
 always @(posedge mem_clk)if(!we)begin
  if(ce1==ce2 || !oe)$fatal(1,"PSRAM contention");
  if(!bhe)ram[offset]<=dq[15:8];if(!ble)ram[offset+1]<=dq[7:0];
 end
 reg [23:0] address=0;reg rd=1,wr=1,cancel=0,core=0;
 reg [21:0] core_address=0;
 integer tick=0;always @(posedge clk)tick<=tick+1;
 reg permit=1;
 wire slot=permit && tick%12==0;
 wire issue,owned,sel,fault;wire [21:0] request_address;wire[7:0] data;
 nes_bg_window659 window(.clk(clk),.reset(reset||!run_enable),.stop(cancel),.slot(slot),.safe(!core),.normal_request(core),
  .mem_ready(ready),.mem_response(response),.mem_error(err),.mem_response_address(reply),.mem_word(word_data),
  .address(address),.read_n(rd),.write_n(wr),.issue(issue),.request_address(request_address),.owned(owned),.selected(sel),.data(data),.fault(fault));
 nes_rom_boot boot(.clk(clk),.mem_clk(mem_clk),.reset(reset),.read_reset(read_reset),.check_enable(check_enable),.check_request(check_request),.check_address(check_address),
  .check_ready(check_ready),.check_response(check_response),.check_response_address(check_response_address),.check_data(check_data),.check_fault(check_fault),
  .load_begin(load_begin),.load_chr32(1'b0),.load_valid(load_valid),.load_end(load_end),.start(start),.stop(stop),.load_data(load_data),.load_ready(load_ready),
  .loaded(loaded),.run_enable(run_enable),.boot_fault(boot_fault),.boot_error(boot_error),.loaded_bytes(loaded_bytes),.rom_chr32(),
  .rom_request(issue || (core && !owned)),.rom_address(issue?request_address:core_address),.rom_ready(ready),.rom_response(response),.rom_error(err),
  .rom_response_address(reply),.rom_data(rom_data),.window_word(word_data),.psram_address(pin_addr),.psram_1ce(ce1),.psram_2ce(ce2),.psram_oe(oe),
  .psram_we(we),.psram_bhe(bhe),.psram_ble(ble),.psram_data(dq));
 reg [23:0] boot_bus=0;wire [7:0] boot_byte;wire boot_oe;
 reg [7:0] image[0:6143];integer a;reg boot_verified=0;
 nes_sink_bus165 client_rom(.clk(clk),.reset(reset),.active(1'b1),.stop(1'b0),.fault(1'b0),
  .address(boot_bus),.read_n(1'b0),.write_n(1'b1),.romsel_n(1'b0),.data_in(8'd0),
  .data_out(boot_byte),.oe_n(boot_oe),.packet_ready(1'b0),.packet_length(9'd0),.packet_data(8'd0));
 initial begin
  $readmemh("sink-program.hex",image);wait(!reset);
  for(a=0;a<6144;a++)begin
   @(negedge clk);boot_bus=a<6080?24'h8000+a:24'hffc0+a-6080;repeat(6)@(negedge clk);
   if(boot_oe || boot_byte!==image[a])$fatal(1,"boot ROM mismatch at %x",boot_bus);
  end
  boot_verified=1;
 end
 task check(input integer i);
  begin @(negedge mem_clk);wait(check_ready);@(negedge mem_clk);check_address=i;check_request=1;
   @(negedge mem_clk);check_request=0;wait(check_response);
   if(check_response_address!==19'(i)||check_data!==native_mem[i])$fatal(1,"logical CHECK %x %x %x",i,check_response_address,check_data);
   @(negedge mem_clk);end
 endtask
 task core_read(input integer i);
  begin @(negedge clk);wait(ready&&!owned);@(negedge clk);core_address=i;core=1;@(negedge clk);core=0;
   wait(response);if(owned || err || reply!==22'(i) || rom_data!==native_mem[{core_address[21],core_address[17:0]}])
    $fatal(1,"core address/data %x",i);
   @(negedge clk);end
 endtask
 task prime(input integer tag);
  begin @(negedge clk);address=24'h520000+tag*16;wr=0;@(negedge clk);wr=1;rd=0;
   wait(data[0] || fault);if(fault)$fatal(1,"prime");@(negedge clk);rd=1;end
 endtask
 integer i,j,g,tag,fd,tiles=0;reg [7:0] expected;
 initial begin
  $readmemh("game.hex",native_mem);repeat(8)@(negedge mem_clk);reset=0;repeat(8)@(negedge mem_clk);
  load_begin=1;@(negedge mem_clk);load_begin=0;
  for(i=0;i<393216;i++)begin wait(load_ready);@(negedge mem_clk);load_valid=1;load_data=native_mem[i];@(negedge mem_clk);load_valid=0;end
  wait(load_ready||loaded_bytes==393216);repeat(24)@(negedge mem_clk);
  load_end=1;@(negedge mem_clk);load_end=0;wait(loaded);
  for(i=0;i<393216;i++)begin
   j=i<262144?i:((i&~15)|((i&7)<<1)|((i>>3)&1));
   if(ram[j]!==native_mem[i])$fatal(1,"PSRAM layout %x",i);
  end
  $display("loaded/check at %t",$time);check_enable=1;
  for(i=0;i<32;i++)begin check(i);check(262144+i);check(393215-i);end
  check_enable=0;repeat(10)@(negedge mem_clk);start=1;@(negedge mem_clk);start=0;wait(run_enable);read_reset=0;repeat(12)@(negedge clk);
  $display("RUN at %t",$time);for(i=0;i<16;i++)core_read(22'h200000+i);
  fd=$fopen("tiles.txt","r");
  while($fscanf(fd,"%d %d",g,tag)==2)begin
   prime(tag);core_read(1234);
   for(i=0;i<16;i++)begin
    address=24'h500000+tag*16+i;rd=0;repeat(3)@(negedge clk);
    expected=native_mem[262144+tag*16+(i>>1)+(i&1)*8];
    if(!sel || fault || data!==expected)$fatal(1,"DMA g=%d tag=%x byte=%d",g,tag,i);
    rd=1;repeat(5)@(negedge clk);
   end
   if(window.consumed!=16)$fatal(1,"incomplete DMA");tiles++;
  end
  if(!boot_verified)$fatal(1,"unchecked bootstrap");
  if(tiles!=19)$fatal(1,"count");
  address=24'h540000;rd=0;#1;if(!sel || data!==1)$fatal(1,"profile discovery");rd=1;
  prime(44);permit=0;
  for(i=0;i<5;i++)begin address=24'h500000+44*16+i;rd=0;repeat(3)@(negedge clk);rd=1;repeat(5)@(negedge clk);end
  if(!fault || window.consumed!=4)$fatal(1,"missing underflow");
  rd=0;cancel=1;#1;if(sel || issue)$fatal(1,"STOP did not revoke");stop=1;
  repeat(12)@(negedge clk);if(run_enable || !we || !oe || check_fault)$fatal(1,"unsafe shutdown");
  $display("PASS659 393216 loader bytes, 96 logical CHECKs, 19x16 DMA, four-byte starvation and STOP");$finish;
 end
 initial begin #365000000;$fatal(1,"watchdog phase=%d loaded=%d",boot.loader.state,loaded_bytes);end
endmodule
