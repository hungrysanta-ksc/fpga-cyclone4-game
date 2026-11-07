`timescale 1ns/1ps
module sender652_tb;
 reg clk=0,nes=0,reset=1,ss=1,sck=0,mosi=0,owned=0;
 always #5.952 clk=~clk;
 always #23.281 nes=~nes;
 wire valid,ready,selected,miso,av,aa,ar,fault,tx,tr,pv,pr,query,release_frame;
 wire [95:0] data,record_data;wire [16:0] prepared;wire [15:0] ag,qgen;
 wire [12:0] qi;wire [2:0] kind;wire [3:0] err;
 reg [15:0] generation;reg [7:0] objects,exceptions;reg [5:0] groups,palettes;reg [2:0] patches;
 reg [63:0] scene[0:16383],answer;reg resp;
 always @(posedge nes)begin resp<=query;if(query)answer<=scene[{kind,qi[10:0]}];end
 nes_native_export203 #(.MAX_CYCLES(33554432)) src(.clk(nes),.reset(reset),.enable(1'b1),.start_permitted(1'b1),
  .discard_permitted(1'b1),.frame_owned(owned),.geometry_valid(1'b1),.frame_generation(generation),
  .patch_count(patches),.row_count(8'd224),.object_count(objects),.exception_count(exceptions),
  .group_count(groups),.palette_count(palettes),.release_frame(release_frame),.query(query),.query_kind(kind),
  .query_index(qi),.query_generation(qgen),.response(resp),.hit(1'b1),.data(answer),.tx_valid(tx),.tx_ready(tr),
  .tx_data(record_data),.ack_valid(pv),.ack_accept(prepared[16]),.ack_generation(prepared[15:0]),.ack_ready(pr),.error(err));
 nes_native_mailbox165 #(.WIDTH(96)) records(nes,clk,reset,tx,tr,record_data,valid,ready,data);
 nes_native_mailbox165 #(.WIDTH(17)) ack(clk,nes,reset,av,ar,{aa,ag},pv,pr,prepared);
 nes_native_spi165 dut(clk,reset,ss,sck,mosi,selected,miso,valid,ready,data,av,ar,aa,ag,fault);
 reg [7:0] rx[0:258];
 // The inherited SPI tasks use 'tx' for the MOSI byte array.
 reg [7:0] spi_tx[0:258];integer fd,wirebytes=0;reg trace_on=0;
 // SPI_TASKS
 integer clocks=0,base_tick,seal_tick,ready_tick,last_token=0,mode=0;
 reg prev_seal=0,prev_ready=0,prev_ack=0;
 always @(posedge clk)begin
  clocks=clocks+1;
  if(!reset && dut.token!=last_token)begin base_tick=clocks;last_token=dut.token;end
  if(!reset && av&&!prev_ack)base_tick=clocks;
  if(dut.sealed&&!prev_seal)seal_tick=clocks;
  if(dut.available&&!prev_ready)ready_tick=clocks;
  prev_seal=dut.sealed;prev_ready=dut.available;prev_ack=av;
  if(!reset && dut.active && (ready||(!ss && dut.command==8'hd1 && dut.reading)||dut.encoding))$fatal(1,"RAM owner");
 end
 integer file_in,g,ng,no,ne,np,nr,nb,r,j,i,n,length,token,out;
 reg [15:0] crc;
 initial begin
  file_in=$fopen("scenes.txt","r");out=$fopen("blocks.txt","w");
  repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
  while(!$test$plusargs("GUARDS") && $fscanf(file_in,"%d%d%d%d%d%d%d",g,ng,no,ne,np,nr,nb)==7)begin
   $readmemh($sformatf("scene%0d.hex",g),scene);
   @(negedge nes);generation=g;groups=ng;objects=no;exceptions=ne;palettes=np;patches=nr;
   owned=1;base_tick=clocks;
   for(i=0;i<nb;i++)begin
    wait(dut.available || err || fault);if(err||fault)$fatal(1,"source fault %d %d",g,i);
    @(negedge clk);
    request(8'hd0,0,0);transfer(8);status_check;
    length={rx[5],rx[6]};token={rx[3],rx[4]};if(!rx[2][0]||length<1||length>256)$fatal(1,"size");
    for(j=0;j<259;j++)spi_tx[j]=0;spi_tx[0]=8'hd1;transfer(length+3);
    $fwrite(out,"%0d %0d %0d %0d ",g,i,ready_tick-base_tick,ready_tick-seal_tick);
    crc=16'hffff;for(j=1;j<=length;j++)crc=c16(crc,rx[j]);
    for(j=1;j<=length+2;j++)$fwrite(out,"%02x",rx[j]);$fwrite(out,"\n");
    if($isunknown(crc) || crc!=={rx[length+1],rx[length+2]})$fatal(1,"D1 CRC %d %d",g,i);
    request(8'hd2,token,0);transfer(8);status_check;
    if(dut.token!=(token+1))$fatal(1,"retire");
    if(i==nb-2)begin request(8'hd3,g,1);transfer(8);status_check;end
   end
   owned=0;repeat(12)@(negedge nes);
  end
  if($test$plusargs("GUARDS"))begin
   $readmemh("scene955.hex",scene);groups=32;patches=0;objects=0;exceptions=0;palettes=1;
   repeat(12)@(negedge nes);generation=955;owned=1;wait(dut.active);
   request(8'hd0,0,0);transfer(8);status_check;
   if(rx[2][0] || dut.read_seen || dut.token)$fatal(1,"unsealed D0");
   wait(dut.available);@(negedge clk);spi_tx[0]=8'hd1;transfer(2);
   if(!fault || dut.read_seen || !dut.available || dut.token)$fatal(1,"partial D1");
   reset=1;owned=0;repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
   // All BG cells are identical: a legacy 256-cell run exceeds the
   // 128-cell scratch capacity. Keep this entire mixed packet in raw RAM.
   for(j=0;j<1056;j++)scene[j]=15'h1234;
   @(negedge nes);generation=956;owned=1;wait(dut.available);
   if(dut.compact || dut.public_size!=dut.used)$fatal(1,"oversized fallback");
   @(negedge clk);request(8'hd0,0,0);transfer(8);status_check;
   length={rx[5],rx[6]};spi_tx[0]=8'hd1;transfer(length+3);
   crc=16'hffff;for(j=1;j<=length;j++)begin
    if(rx[j]!==dut.buffer[j-1])$fatal(1,"fallback byte");crc=c16(crc,rx[j]);end
   if($isunknown(crc)||crc!=={rx[length+1],rx[length+2]})$fatal(1,"fallback CRC");
   reset=1;owned=0;repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
   $readmemh("scene955.hex",scene);g=954;groups=32;
  end
  // Cancel a partially encoded block and reject an old POP after restart.
  @(negedge nes);generation=g+1;owned=1;wait(dut.active);repeat(32)@(negedge clk);
  reset=1;owned=0;repeat(12)@(negedge clk);reset=0;repeat(12)@(negedge clk);
  if(dut.available || dut.token || dut.used || dut.codec.write_en)$fatal(1,"STOP leaked ownership");
  request(8'hd2,16'hffff,0);transfer(8);if(!fault||dut.token)$fatal(1,"stale POP");
  $fclose(out);$display("PASS652");$finish;
 end
 initial begin #2000000000;$fatal(1,"timeout");end
endmodule
