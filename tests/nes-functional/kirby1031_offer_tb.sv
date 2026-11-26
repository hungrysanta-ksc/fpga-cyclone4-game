// Same captured input, same D0/D1 schedule, independently movable producer.
`timescale 1ns/1ps
module kirby1031_offer_tb;
 reg clk=0, reset=1, valid=0;
 always #5.952 clk=~clk;
 `include "spi200_bus.svh"
 wire ready,fault;
 reg [95:0] record_word;
`ifdef SHARED1032
 wire offer_phase;
 nes_display1010 trace_clock(.clk(clk),.reset(reset),.active(!reset),.cancel(1'b0),.offer_phase(offer_phase));
`endif
 nes_native_spi165 dut(.clk(clk),.reset(reset),.SPI_SS(ss197),.SPI_SCK(sck197),.SPI_MOSI(mosi197),
`ifdef SHARED1032
 .offer_phase(offer_phase),
`endif
 .selected(selected197),.miso(miso197),.record_valid(valid),.record_ready(ready),.record_data(record_word),
 .ack_ready(1'b1),.fault(fault));

 integer cycle=0,available_cycle=-1,positive_cycle=-1,read_cycle=-1;
 integer mode,records,nbytes,seq,expected_age,i,k;
 reg [95:0] words[0:255];
 reg [7:0] expected[0:257],received;
 string wordfile,bytefile;
 always @(posedge clk)begin
  cycle=cycle+1;
  if(!reset && dut.available && seq==0)begin
   if(available_cycle<0)available_cycle=cycle;
   if(!dut.ss[1] && dut.sck[1] && !dut.prev_sck && dut.bit_count==7 && dut.cursor==511)begin
    if(dut.incoming=='hd0 && positive_cycle<0)positive_cycle=cycle;
    if(dut.incoming=='hd1 && read_cycle<0)read_cycle=cycle;
   end
  end
 end
 task automatic status_cmd(input byte op,input integer token);
  reg [7:0] request[0:7];reg [7:0] c;
  integer j;
  begin
   request[0]=op;request[1]=0;request[2]=token>>8;request[3]=token;
   request[4]=0;request[5]=255;request[6]=0;request[7]='ha5;
   for(j=0;j<6;j++)request[6]=crc8_197(request[6],request[j]);
   begin197();for(j=0;j<8;j++)byte197(request[j],rx197[j]);end197();
   c=0;for(j=1;j<7;j++)c=crc8_197(c,rx197[j]);
   if(rx197[1]!==8'hd6 || rx197[2][7]!==0 || rx197[7]!==c)$fatal(1,"status");
  end
 endtask
 initial begin
  seq=0;
  if(!$value$plusargs("MODE=%d",mode) || !$value$plusargs("COUNT=%d",records)
     || !$value$plusargs("BYTES=%d",nbytes) || !$value$plusargs("WORDS=%s",wordfile)
     || !$value$plusargs("D1=%s",bytefile))$fatal;
  $readmemh(wordfile,words,0,records-1);
  $readmemh(bytefile,expected,0,nbytes+1);
  repeat(8)@(negedge clk);reset=0;
  status_cmd('hd0,0);
  if(rx197[2][0]!==0 || rx197[5]!==0)$fatal(1,"false offer");
  fork
   begin
    if(mode==1)repeat(1008000)@(negedge clk); // 12 ms at nominal 84 MHz
    for(i=0;i<records;i++)begin
     @(negedge clk);while(!ready)@(negedge clk);
     record_word=words[i];valid=1;@(negedge clk);valid=0;
    end
   end
   begin
    if(mode==1 || mode==2)begin
     // Same bus calendar in both arms, no input-status poll in this interval.
     repeat(100)begin
      begin197();byte197('he1,received);
      for(k=0;k<116;k++)byte197(0,received);
      end197();
     end
     repeat(24000)@(negedge clk);
    end
    wait(dut.available);
    status_cmd('hd0,0);
    if({rx197[5],rx197[6]}!==nbytes || {rx197[3],rx197[4]}!==0 || rx197[2][0]!==1)$fatal(1,"D0 ABI");
    if(mode==3)repeat(1008000)@(negedge clk); // Positive D0 cached before service
    if(mode==4)repeat(4300000)@(negedge clk); // saturating age
    begin197();byte197('hd1,received);
    for(k=0;k<nbytes+2;k++)begin
     byte197(0,received);if(received!==expected[k])$fatal(1,"payload/CRC offset %0d",k);
    end
    end197();
    status_cmd('hd2,0);
    expected_age=(read_cycle-available_cycle)>>15;
    if(expected_age>127)expected_age=127;
`ifdef SHARED1032
    if($isunknown(rx197[5]) || rx197[5][7:1]<expected_age ||
       rx197[5][7:1]>expected_age+1)$fatal(1,"shared tick vs absolute cycle oracle");
    expected_age=rx197[5][7:1];
`endif
    if(rx197[5][7:1]!==expected_age || {rx197[5][0],rx197[6]}!==nbytes || fault)$fatal(1,"receipt age/length");
    seq=1;
    status_cmd('hd0,0);
    if({rx197[3],rx197[4]}!==1 || rx197[2][0]!==0 || rx197[5]!==0)$fatal(1,"retire");
   end
  join
  // Common reset while a fresh header is available must discard its age and token.
  for(i=0;i<records;i++)begin
   @(negedge clk);while(!ready)@(negedge clk);
   record_word=words[i];valid=1;@(negedge clk);valid=0;
  end
  wait(dut.available);repeat(35000)@(negedge clk);
  @(negedge clk);reset=1;repeat(4)@(negedge clk);reset=0;status_cmd('hd0,0);
  if(fault || dut.first_wait!==0 || dut.first_read!==0 || rx197[2][0]!==0 ||
     {rx197[3],rx197[4]}!==0 || rx197[5]!==0)$fatal(1,"stale offer after common reset");
  $display("PASS1031 mode=%0d bytes=%0d available=%0d positive=%0d D1=%0d age=%0d",
           mode,nbytes,available_cycle,positive_cycle,read_cycle,expected_age);
  $finish;
 end
 initial begin #90000000;$fatal(1,"timeout mode=%0d",mode);end
endmodule
