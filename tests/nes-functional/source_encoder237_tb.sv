// SPDX-License-Identifier: MIT
// Synthetic canonical bytes test the encoder boundaries independently of the
// recorded collector/SPI integration. Ready stalls are deterministic.
`timescale 1ns/1ps
module source_encoder237_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort_source=0,start=0,frame_owned=1,geometry_valid=1;
 reg [15:0] frame_generation=65535,ack_generation=0;
 reg [31:0] content_epoch=1,frame_serial=1;reg [2:0] patch_count=0;
 reg feeding=0,in_bad_offset=0,raw_bad_hit=0,raw_bad_width=0,raw_silent=0;
 reg ack_valid=0,ack_accept=1,auto_ack=0,check_output=0;
 reg [7:0] geometry[0:5740],raw[0:1791],expected[0:19999];integer sizes[0:1023];
 integer sent=0,cycle=0,packet=0,packet_byte=0,at=0,records=0,checks=0,writes=0;
 wire in_valid=feeding;wire [7:0] in_data=geometry[sent<5741?sent:0];
 wire [12:0] in_offset=sent+in_bad_offset;
 wire in_ready,start_ready,raw_query,record_valid,byte_valid,record_flush,ack_ready,done;
 wire [12:0] raw_index;wire [7:0] record_length,byte_data;wire [3:0] fault;
 reg raw_response=0,raw_hit=1;reg [63:0] raw_data=0;
 wire record_ready=cycle%11!=0,byte_ready=cycle%7!=0&&cycle%13!=0;
 nes_source_encoder237 dut(.*);
 always @(posedge clk)begin
  cycle<=cycle+1;raw_response<=0;
  if(!reset)begin
   if(dut.a_we&&dut.b_we&&dut.a_addr==dut.b_addr)$fatal(1,"scratch write collision");
   if((dut.a_we&&dut.a_addr>=635)||(dut.b_we&&dut.b_addr>=635)||(dut.base_we&&dut.base_addr>=5741))$fatal(1,"RAM bounds");
   if(dut.base_we)writes++;
   if(in_valid&&in_ready)begin sent<=sent+1;if(sent==5740)feeding<=0;end
   if(raw_query&&!raw_silent)begin
    raw_response<=1;raw_hit<=!raw_bad_hit;raw_data<={56'd0,raw[raw_index]}|(raw_bad_width?64'h100:64'd0);
   end
   if(check_output&&record_valid&&record_ready)begin
    if(packet>=records||record_length!=sizes[packet]||packet_byte)$fatal(1,"record header case%0d packet%0d got%0d expected%0d",c,packet,record_length,sizes[packet]);
   end
   if(check_output&&byte_valid&&byte_ready)begin
    if(byte_data!==expected[at])$fatal(1,"byte case%0d packet%0d byte%0d got%h expected%h",c,packet,packet_byte,byte_data,expected[at]);
    at++;packet_byte++;
    if(packet_byte==sizes[packet])begin packet++;packet_byte=0;end
   end
  end
 end
 always @(negedge clk)if(auto_ack&&ack_ready)begin ack_valid=1;ack_generation=frame_generation;end
 else if(auto_ack)ack_valid=0;
 task fresh;
  begin
   reset=1;abort_source=0;start=0;feeding=0;ack_valid=0;auto_ack=0;check_output=0;
   frame_owned=1;geometry_valid=1;frame_generation=65535;content_epoch=1;frame_serial=1;patch_count=0;
   in_bad_offset=0;raw_bad_hit=0;raw_bad_width=0;raw_silent=0;sent=0;ack_accept=1;
   repeat(4)@(negedge clk);reset=0;repeat(2)@(negedge clk);
  end
 endtask
 task launch;
  begin
   wait(start_ready);@(negedge clk);sent=0;feeding=1;start=1;
   @(negedge clk);start=0;
  end
 endtask
 task rejected(input integer code);
  integer w;begin
   wait(fault);@(negedge clk);w=writes;
   if(fault!=code||dut.base_valid)$fatal(1,"fault code%0d expected%0d valid%0d",fault,code,dut.base_valid);
   repeat(12)@(negedge clk);
   if(in_ready||record_valid||byte_valid||raw_query||ack_ready||start_ready||done||writes!=w)$fatal(1,"fault not quiescent");
   checks++;
  end
 endtask
 integer c,i,j,rf,n,ncases,offset;string name;
 initial begin
  if(!$value$plusargs("CASES=%d",ncases))ncases=20;
  fresh;
  for(c=0;c<ncases;c++)begin
   name=$sformatf("case%0d.geometry",c);$readmemh(name,geometry);
   name=$sformatf("case%0d.raw",c);$readmemh(name,raw);
   name=$sformatf("case%0d.expected",c);rf=$fopen(name,"r");if(!rf)$fatal(1,"expected file");
   if($fscanf(rf,"%d",records)!=1)$fatal(1,"record count");offset=0;
   for(i=0;i<records;i++)begin
    if($fscanf(rf,"%d",sizes[i])!=1)$fatal(1,"length");
    for(j=0;j<sizes[i];j++)begin if($fscanf(rf,"%h",expected[offset])!=1)$fatal(1,"byte EOF");offset++;end
   end
   $fclose(rf);packet=0;packet_byte=0;at=0;check_output=1;auto_ack=1;
   frame_serial=c+1;frame_generation=(65535+c)&65535;patch_count=c%8;launch;
   wait(done);@(negedge clk);
   if(fault||sent!=5741||packet!=records||at!=offset||dut.base_serial!=frame_serial)$fatal(1,"completion %0d",c);
   for(i=0;i<5741;i++)if(dut.base[i]!==geometry[i])$fatal(1,"speculative base %0d/%0d",c,i);
   checks++;$display("ENCODER237 case=%0d packets=%0d bytes=%0d",c,packet,at);
  end
  // Retained-base epoch and serial may not silently change.
  check_output=0;auto_ack=0;content_epoch=2;frame_serial++;launch;rejected(1);
  fresh;frame_serial=2;launch;rejected(1);
  fresh;frame_serial=0;launch;rejected(1);
  fresh;frame_serial=32'hffffffff;launch;rejected(1);
  fresh;in_bad_offset=1;launch;rejected(3);
  fresh;launch;wait(dut.cursor>100);@(negedge clk);frame_owned=0;rejected(2);
  fresh;launch;wait(dut.cursor>100);@(negedge clk);frame_generation++;rejected(2);
  fresh;launch;wait(dut.cursor>100);@(negedge clk);abort_source=1;rejected(4);
  fresh;launch;wait(dut.cursor>100);@(negedge clk);ack_valid=1;ack_generation=frame_generation;rejected(5);
  fresh;patch_count=1;raw_bad_hit=1;launch;rejected(3);
  fresh;patch_count=1;raw_bad_width=1;launch;rejected(3);
  fresh;patch_count=1;raw_silent=1;launch;wait(raw_query);repeat(50)@(negedge clk);
  if(fault||done||raw_index!=0)$fatal(1,"missing response invented completion");abort_source=1;rejected(4);
  fresh;launch;wait(ack_ready);@(negedge clk);ack_valid=1;ack_generation=12;rejected(5);
  fresh;launch;wait(ack_ready);@(negedge clk);ack_valid=1;ack_generation=frame_generation;ack_accept=0;rejected(5);
  fresh;launch;wait(byte_valid&&dut.record_length==243);@(negedge clk);abort_source=1;rejected(4);
  // Common-reset cold replay must overwrite old/unpublished base contents.
  fresh;auto_ack=1;launch;wait(done);@(negedge clk);
  if(fault||!dut.base_valid||dut.base_serial!=1)$fatal(1,"cold replay");checks++;
  $display("PASS ENCODER237 checks=%0d normal=%0d",checks,ncases);$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog state=%0d cursor=%0d",dut.state,dut.cursor);end
endmodule
