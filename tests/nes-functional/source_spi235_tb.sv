// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module source_spi235_tb;
 parameter real PHASE=3.5;
 parameter bit GUARDS_ONLY=0;
 reg src_clk=0,host_clk=0,run_source=1,run_host=1,reset=1,abort_source=0;
 always #22.727 if(run_source)src_clk=~src_clk;
 initial begin #(PHASE);forever #5.952 if(run_host)host_clk=~host_clk;end
 reg record_valid=0,record_flush=0,byte_valid=0;reg [7:0] record_length=0,byte_data=0;
 wire record_ready,byte_ready,selected,miso,ack_valid,ack_accept,source_fault,host_fault;
 wire [15:0] ack_generation;reg ack_ready=1,ss=1,sck=0,mosi=0;
 nes_source_spi235 dut(.src_clk(src_clk),.host_clk(host_clk),.reset(reset),.abort_source(abort_source),
  .record_valid(record_valid),.record_ready(record_ready),.record_length(record_length),.record_flush(record_flush),
  .byte_valid(byte_valid),.byte_ready(byte_ready),.byte_data(byte_data),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),
  .selected(selected),.miso(miso),.ack_valid(ack_valid),.ack_ready(ack_ready),.ack_accept(ack_accept),.ack_generation(ack_generation),
  .source_fault(source_fault),.host_fault(host_fault));
 reg [7:0] tx[0:258],rx[0:258],payload[0:242];
 integer rf,bf,rc,n,j,k,flush,frames,acks=0,blocks=0,wirebytes=0,overlap=0,fullwait=0,checks=0;
 integer length;reg [15:0] token,crc;reg normal=1,ended,producer_done=0;
 function automatic [7:0] c8(input [7:0] c0,b);
  reg [7:0] c;integer i;begin c=c0^b;for(i=0;i<8;i++)c=c[7]?(c<<1)^7:c<<1;c8=c;end
 endfunction
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer i;begin c=c0^{b,8'd0};for(i=0;i<8;i++)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end
 endfunction
 always @(posedge src_clk)if(!reset)begin
  if(byte_valid&&byte_ready)begin
   if(dut.block_valid[dut.bank])$fatal(1,"write published bank");
   if(dut.block_valid[~dut.bank])overlap++;
  end
  if(record_valid&&!record_ready&&dut.busy==3)fullwait++;
  if(normal&&ack_valid&&ack_ready)begin
   acks++;if(!ack_accept||ack_generation!=acks)$fatal(1,"prepared ACK %0d/%0d",ack_generation,acks);
  end
 end
 task request(input [7:0] cmd,input [15:0] tok,input [7:0] arg);
  integer i;reg [7:0] c;begin
   tx[0]=cmd;tx[1]=0;tx[2]=tok[15:8];tx[3]=tok[7:0];tx[4]=arg;tx[5]=~arg;c=0;
   for(i=0;i<6;i++)c=c8(c,tx[i]);tx[6]=c;tx[7]=8'ha5;
  end
 endtask
 task transfer(input integer size);
  integer i,b;begin
   #2000;ss=0;#2000;
   for(i=0;i<size;i++)begin rx[i]=0;for(b=7;b>=0;b--)begin
    mosi=tx[i][b];#190.476190476;sck=1;rx[i][b]=selected?miso:0;#190.476190476;sck=0;
   end end
   #2000;ss=1;#2000;wirebytes+=size;
  end
 endtask
 task status;
  integer i;reg [7:0] c;begin
   request(8'hd0,0,0);transfer(8);c=0;for(i=1;i<7;i++)c=c8(c,rx[i]);
   if(rx[1]!=8'hd8||rx[7]!=c||rx[2][7])$fatal(1,"bad status %02x %02x",rx[1],rx[2]);
  end
 endtask
 task send(input integer size,input bit last_record);
  integer i;begin
   @(negedge src_clk);record_valid=1;record_length=size;record_flush=last_record;
   do @(posedge src_clk);while(!record_ready);
   @(negedge src_clk);record_valid=0;
   for(i=0;i<size;i++)begin
    if(i%7==3)repeat(2)@(negedge src_clk);
    byte_data=payload[i];byte_valid=1;
    do @(posedge src_clk);while(!byte_ready);
    @(negedge src_clk);byte_valid=0;
   end
  end
 endtask
 task fresh;
  begin
   reset=1;record_valid=0;byte_valid=0;abort_source=0;ss=1;sck=0;ack_ready=1;
   #300;run_source=1;run_host=1;#300;reset=0;repeat(20)@(negedge src_clk);
   if(source_fault||host_fault||dut.block_valid||ack_valid)$fatal(1,"reset residue");
  end
 endtask
 task fill;
  integer i;begin for(i=0;i<17;i++)payload[i]=i+7;send(17,1);wait(dut.block_valid[0]);status;end
 endtask
 task read_block;
  integer i;begin
   length=rx[6];token={rx[3],rx[4]};if(length<1||length>248)$fatal(1,"length");
   for(i=0;i<259;i++)tx[i]=0;tx[0]=8'hd1;transfer(length+3);
   crc=16'hffff;for(i=1;i<=length;i++)crc=c16(crc,rx[i]);
   if(crc!={rx[length+1],rx[length+2]})$fatal(1,"CRC");
  end
 endtask
 initial begin
  if(!GUARDS_ONLY)begin
  rf=$fopen("records.hex","r");bf=$fopen("blocks.txt","w");if(!rf||!bf)$fatal(1,"files");
  if($fscanf(rf,"%d",frames)!=1)$fatal(1,"frames");fresh;
  fork
   begin
    integer pf;pf=0;
    while($fscanf(rf,"%h %h",n,flush)==2)begin
     for(j=0;j<n;j++)if($fscanf(rf,"%h",payload[j])!=1)$fatal(1,"record EOF");
     send(n,flush!=0);
     if(flush)begin pf++;wait(acks==pf);end
    end
    producer_done=1;
   end
   begin
    integer hf;hf=0;
    while(hf<frames)begin
     status;
     if(rx[2][0])begin
      read_block;
      $fwrite(bf,"%0d %0d ",token,length);for(k=1;k<=length;k++)$fwrite(bf,"%02x",rx[k]);$fwrite(bf,"\n");
      ended=length>=6&&rx[length-5]==255&&rx[length-4]==255&&rx[length-3]==0&&rx[length-2]==4;
      // Repeated read keeps ownership; next bank may fill simultaneously.
      if(blocks%17==0)begin status;read_block;checks++;end
      request(8'hd2,token,0);transfer(8);if(host_fault)$fatal(1,"POP");blocks++;
      if(ended)begin hf++;status;request(8'hd3,hf,1);transfer(8);end
     end
    end
   end
  join
  $fclose(rf);$fclose(bf);normal=0;
  if(!producer_done||source_fault||host_fault||acks!=frames||!overlap||!fullwait)$fatal(1,"normal/overlap evidence");
  $display("NORMAL235 frames=%0d blocks=%0d wirebytes=%0d overlapwrites=%0d fullwait=%0d rereads=%0d",frames,blocks,wirebytes,overlap,fullwait,checks);
  end else begin normal=0;fresh;end
  // Each bad control leaves the same published bank/token owned until reset.
  for(n=0;n<8;n++)begin
   fresh;fill;
   case(n)
    0:begin request(8'hd2,0,0);transfer(8);end // no complete read
    1:begin read_block;request(8'hd2,1,0);transfer(8);end
    2:begin request(8'hd0,0,0);tx[6]^=1;transfer(8);end
    3:begin tx[0]=8'hd1;transfer(2);end
    4:begin tx[0]=8'hd1;transfer(21);end // one byte too many
    5:begin read_block;request(8'hd2,0,0);tx[5]^=1;transfer(8);end
    6:begin read_block;request(8'hd2,0,0);transfer(7);end
    7:begin // Complete D1 command, then only three bits of payload clock.
     #2000;ss=0;#2000;
     for(k=7;k>=0;k--)begin mosi=(8'hd1>>k)&1;#190.476190476;sck=1;#190.476190476;sck=0;end
     repeat(3)begin mosi=0;#190.476190476;sck=1;#190.476190476;sck=0;end
     #2000;ss=1;#2000;
    end
   endcase
   repeat(20)@(negedge src_clk);
   if(!host_fault||!source_fault||dut.token!=0||!dut.block_valid[0]||record_ready||byte_ready)$fatal(1,"fault ownership %0d",n);
   checks++;$display("FAULT235 case=%0d retained",n);
  end
  fresh;fill;request(8'h60,0,0);transfer(8);if(host_fault||dut.token)$fatal(1,"foreign command");checks++;
  status;read_block;request(8'hd2,0,0);transfer(8);request(8'hd2,0,0);transfer(8);
  if(!host_fault||dut.token!=1)$fatal(1,"duplicate POP");checks++;
  fresh;fill;dut.token=16'hffff;status;read_block;request(8'hd2,16'hffff,0);transfer(8);
  if(!host_fault||dut.token!=65535||!dut.block_valid[0])$fatal(1,"token wrap");checks++;
  fresh;fill;@(negedge src_clk);abort_source=1;repeat(20)@(negedge host_clk);
  if(!source_fault||!host_fault||byte_ready||record_ready)$fatal(1,"source abort");checks++;
  fresh;ack_ready=0;request(8'hd3,123,1);transfer(8);wait(ack_valid);
  repeat(20)@(negedge src_clk);if(!ack_accept||ack_generation!=123)$fatal(1,"ACK hold");
  request(8'hd3,124,1);transfer(8);if(!host_fault)$fatal(1,"ACK overrun");checks++;
  // Reset while either domain is stopped, with published payload and ACK.
  for(n=0;n<2;n++)begin
   fresh;fill;
   if(n==0)run_source=0;else run_host=0;
   reset=1;#300;if(selected||record_ready||byte_ready||ack_valid)$fatal(1,"async reset gate");
   reset=0;#300;if(record_ready||byte_ready)$fatal(1,"peer not restarted");
   fresh;status;if(rx[2][0]||dut.token)$fatal(1,"stopped reset old block");checks++;
  end
  fresh;@(negedge src_clk);record_length=244;record_valid=1;repeat(3)@(negedge src_clk);record_valid=0;
  if(!source_fault)$fatal(1,"oversize record");checks++;
  fresh;@(negedge src_clk);record_length=0;record_valid=1;repeat(3)@(negedge src_clk);record_valid=0;
  if(!source_fault)$fatal(1,"empty record");checks++;
  fresh;@(negedge src_clk);record_length=17;record_flush=1;record_valid=1;
  do @(posedge src_clk);while(!record_ready);
  @(negedge src_clk);record_valid=0;byte_valid=1;byte_data=8'h5a;
  @(negedge src_clk);byte_valid=0;abort_source=1;repeat(20)@(negedge src_clk);
  if(!source_fault||dut.block_valid||ack_valid)$fatal(1,"partial unpublished abort");checks++;
  fresh;status;if(rx[2][0])$fatal(1,"partial old payload survived reset");checks++;
  $display("PASS SPI235 checks=%0d phase=%0f",checks,PHASE);$finish;
 end
 initial begin #2000000000;$fatal(1,"watchdog");end
endmodule
