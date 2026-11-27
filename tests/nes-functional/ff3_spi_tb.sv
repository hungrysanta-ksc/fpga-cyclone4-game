// Public SPI pins, no hierarchical writes to the endpoint.
`timescale 1ns/1ps
module ff3_spi_tb #(parameter BOOT=0, LINK=0);
 reg clk=0;always #5 clk=!clk;
 reg reset=1,ss=1,sck=0,mosi=0,paused=0,sleeping=0,restored=0,drained=0;
 reg stream_ena=0,stream_rnw=0;reg [25:0] stream_addr=0;reg [63:0] stream_write=0;reg [7:0] stream_be=255;
 wire selected,miso,hold_core,boot_hold,save,load,stream_done,bat_read,bat_write;
 wire [63:0] stream_read;wire [12:0] bat_addr;wire [7:0] bat_data;
 reg bat_valid=0;reg [7:0] bat_q=0;
 wire link_sleep,link_restored,link_req,link_read;
 wire [25:0] link_address;
 wire [63:0] link_word,reg_write_data;
 wire [9:0] reg_index;
 wire reg_write,ram_write;
 wire [24:0] ram_address;
 wire [7:0] ram_wdata,link_mask;
 wire [2:0] ram_region;
 logic [63:0] image[0:2657];
 bit vary_live;
 int link_commits,ram_writes;
 wire [63:0] reg_data=64'h1050413255667700 ^ {54'd0,reg_index} ^ {64{vary_live}};
 wire [7:0] ram_data=ram_address[7:0]^ram_address[12:5]^{5'd0,ram_region};
 if(LINK)begin:linked
  savestates walker(.clk(clk),.reset_in(reset),.save(save),.load(load),.paused(paused),
   .savestate_address(32'd58720256),.increaseSSHeaderCount(1'b0),
   .sleep_savestate(link_sleep),.load_done(link_restored),.BUS_Din(reg_write_data),
   .BUS_Dout(reg_data),.BUS_Adr(reg_index),.BUS_wren(reg_write),
   .Save_RAMType(ram_region),.Save_RAMAddr(ram_address),.Save_RAMRdEn(),
   .Save_RAMWrEn(ram_write),.Save_RAMReadData(ram_data),.Save_RAMWriteData(ram_wdata),
   .bus_out_Adr(link_address),.bus_out_ena(link_req),.bus_out_rnw(link_read),
   .bus_out_Din(link_word),.bus_out_Dout(stream_read),
   .bus_out_be(link_mask),.bus_out_done(stream_done));
  always @(posedge clk)begin
   if(reg_write)begin
    if(reg_write_data!==image[reg_index+1]) $fatal(1,"register commit %d",reg_index);
    link_commits++;
   end
   if(ram_write)begin
    if(ram_wdata!==ram_data)$fatal(1,"RAM restore region=%d address=%h",ram_region,ram_address);
    ram_writes++;
   end
  end
 end
 nes_checkpoint_spi #(.BOOT_HOLD(BOOT)) dut(.sleeping(LINK?link_sleep:sleeping),
  .restored(LINK?link_restored:restored),.stream_ena(LINK?link_req:stream_ena),
  .stream_rnw(LINK?link_read:stream_rnw),.stream_addr(LINK?link_address:stream_addr),
  .stream_write(LINK?link_word:stream_write),.stream_be(LINK?link_mask:stream_be),.*);
 // Exercise the actual shared MISO selection. The stopped-history decoder
 // claims all A0..BF commands even during RUN.
 wire observer_selected, observer_reply;
 nes_run_observer134 observer(.clk(clk),.reset(reset),.SPI_SS(ss),.SPI_SCK(sck),
   .SPI_MOSI(mosi),.selected(observer_selected),.miso(observer_reply),
   .core_reset(1'b0),.cpu_sample(1'b0),.rom_fault(1'b0),.history_sample157(96'd0),
   .history_enable180(1'b0),.pad_event(1'b0),.pad_buttons(8'd0),.rom_error(4'd0),
   .ppu_fault_state154(64'd0),.fault_trigger(1'b0),.fault_context(64'd0));
 wire bus_reply=selected&&!observer_selected?miso:
                observer_selected&&!selected?observer_reply:1'bz;
 always @(posedge clk) if(selected && observer_selected)$fatal(1,"shared SPI select collision");
 integer saves=0,loads=0,acks=0,writes=0;reg [63:0] last_load;
 always @(posedge clk)begin
  if(save)saves++;if(load)loads++;
  if(stream_done)begin acks++;last_load=stream_read;end
  if(bat_write)writes++;
  bat_valid<=bat_read;
  if(bat_read)bat_q<=bat_addr[7:0]^8'h57;
 end
 reg [7:0] tx[13],rx[13];
 function automatic byte crc_step(input byte c,input byte b);
  c^=b; repeat(8)c=c[7]?((c<<1)^7):(c<<1);return c;
 endfunction
 task automatic packet(input byte op,input int address,input logic [63:0] value,input int size=13,input bit corrupt=0);
  byte crc;
  tx[0]=8'h59;tx[1]=op;tx[2]=address>>8;tx[3]=address;
  for(int j=0;j<8;j++)tx[4+j]=value[8*j+:8];
  crc=0;for(int j=0;j<12;j++)crc=crc_step(crc,tx[j]);tx[12]=crc^corrupt;
  ss=0;#100;
  for(int j=0;j<size;j++)begin
   for(int i=7;i>=0;i--)begin mosi=(j<13)?tx[j][i]:0;#60;sck=1;#45;
    if(j<13)rx[j][i]=bus_reply;
    if(j>0 && !selected)$fatal(1,"lost chip select");#15;sck=0;
   end
  end
  #65;ss=1;#100;
  if(size==13)begin 
   crc=crc_step(0,8'h59);for(int j=1;j<12;j++)crc=crc_step(crc,rx[j]);
   if(rx[12]!==crc)$fatal(1,"response CRC %h/%h",rx[12],crc);
  end
 endtask
 task automatic issue(input bit rd,input int idx,input logic [63:0] value);
  @(negedge clk);stream_addr=26'd58720256+2*idx;stream_rnw=rd;stream_write=value;stream_ena=1;
  @(negedge clk);stream_ena=0;
 endtask
 initial if(LINK)begin #300ms;$fatal(1,"SPI/walker timeout acks=%0d",acks);end
 task automatic linked_roundtrip;
  int idx;
  logic [63:0] word_value;
  paused=1;drained=1;packet(1,0,0);packet(3,0,0);
  for(int n=0;n<2658;n++)begin
   idx=(n+1)%2658;
   wait(dut.pending);@(negedge clk);
   if(idx==1)vary_live=1;
   packet(0,0,0);
   if(!rx[1][2] || rx[1][7] || {rx[2],rx[3]}!=idx)$fatal(1,"capture index %d",idx);
   for(int i=0;i<8;i++)word_value[8*i+:8]=rx[4+i];
   image[idx]=word_value;
   if(idx==1 && word_value!==64'h1050413255667700)$fatal(1,"capture changed while waiting");
   if(idx==0 && word_value!==64'h000014c400000000)$fatal(1,"header");
   vary_live=0;
   if(idx==1)begin
    packet(5,idx+4096,word_value);packet(5,idx,word_value^64'd1);
    if(acks)$fatal(1,"wrong identity or echo accepted");
   end
   packet(5,idx,word_value);
  end
  wait(!link_sleep);packet(0,0,0);
  if(!rx[1][5] || rx[1][7] || acks!=2658)$fatal(1,"save finish");
  packet(4,0,0);
  for(int n=0;n<2658;n++)begin
   wait(dut.pending);@(negedge clk);
   if(n==1)begin
    packet(6,n,~image[n],9);packet(6,n,~image[n],13,1);packet(6,n+4096,~image[n]);
    if(link_commits || acks!=2659)$fatal(1,"unvalidated bytes applied");
   end
   packet(6,n,image[n]);
  end
  wait(!link_sleep);packet(0,0,0);
  if(!rx[1][5] || rx[1][7] || acks!=5316 || link_commits!=60 || ram_writes!=20744)
    $fatal(1,"restore finish acks=%d registers=%d RAM=%d",acks,link_commits,ram_writes);
  packet(2,0,0);if(hold_core)$fatal(1,"resume");
  $display("PASS linked FF3 SPI/walker 2658 words each direction, echo, CRC, retry, exact indices");
 endtask
 initial begin
  repeat(4)@(negedge clk);reset=0;
  if(LINK)begin linked_roundtrip();$finish;end
  if(BOOT)begin
    drained=1;packet(0,0,0);if(rx[1][1:0]!=3 || !boot_hold)$fatal(1,"boot hold");
    packet(3,0,0);if(saves || !boot_hold)$fatal(1,"capture during boot");
    packet(8,21,93);if(writes!=1 || bat_data!=93 || !boot_hold)$fatal(1,"boot SRAM write");
    packet(2,0,0);if(boot_hold || hold_core)$fatal(1,"boot release");
    reset=1;repeat(3)@(negedge clk);if(!boot_hold || !hold_core)$fatal(1,"STOP failed to rearm boot");
    reset=0;paused=0;drained=1;
    packet(1,0,0);packet(0,0,0);
    if(boot_hold || !hold_core || rx[1][1:0]!=1)$fatal(1,"cold slot released capture or claimed SAFE early");
    packet(4,0,0);if(loads)$fatal(1,"restore before real pause");
    paused=1;drained=0;packet(4,0,0);if(loads)$fatal(1,"restore before drain");
    drained=1;packet(0,0,0);if(rx[1][1:0]!=3)$fatal(1,"missing SAFE");
    packet(4,0,0);if(loads!=1 || !hold_core)$fatal(1,"cold restore not accepted");
    reset=1;repeat(3)@(negedge clk);if(!boot_hold || !hold_core)$fatal(1,"partial restore STOP");
    $display("PASS FF3 boot SRAM before CPU release");$finish;
  end
  packet(1,0,0,12);if(hold_core)$fatal(1,"short command");
  packet(1,0,0,14);if(hold_core)$fatal(1,"long command");
  packet(1,0,0,13,1);if(hold_core)$fatal(1,"bad CRC");
  packet(1,0,0);packet(3,0,0);if(!hold_core || saves)$fatal(1,"pause gate");
  paused=1;drained=1;
  packet(8,13'h1fff,8'hc4);if(writes!=1 || bat_data!=8'hc4 || bat_addr!=8191)$fatal;
  packet(7,13'h101,0);packet(0,0,0);if(!rx[1][6]||rx[4]!=8'h56)$fatal;
  packet(3,0,0);if(saves!=1)$fatal;sleeping=1;
  // If the stream arrives after the reply flags were sampled, the word
  // must first appear in the next transaction, complete and byte-aligned.
  fork
    packet(0,0,0);
    begin wait(dut.count==5);issue(0,1,64'h123456789abcdef0);end
  join
  if(rx[1][2])$fatal(1,"late capture exposed in old reply");
  for(int length=5;length<=11;length++)begin
    packet(5,1,64'h123456789abcdef0,length);
    if(acks)$fatal(1,"truncated echo acknowledged");
    packet(0,0,0);
    for(int lane=0;lane<8;lane++)begin
      if(rx[4+lane]!==((64'h123456789abcdef0>>(8*lane))&8'hff))
        $fatal(1,"capture retry shifted length=%0d lane=%0d",length,lane);
    end
  end
  packet(6,1,~64'h123456789abcdef0);packet(8,1,0);
  packet(0,0,0);
  if(!rx[1][2]||rx[3]!=1||rx[4]!=8'hf0||rx[11]!=8'h12)$fatal(1,"snapshot status");
  packet(5,2,64'h123456789abcdef0);packet(5,1,64'h123456789abcdef1);if(acks)$fatal(1,"bad ACK");
  packet(5,1,64'h123456789abcdef0);packet(5,1,64'h123456789abcdef0);if(acks!=1)$fatal(1,"retry");
  sleeping=0;packet(0,0,0);packet(0,0,0);if(!rx[1][5]||rx[1][7])$fatal(1,"capture done");
  packet(4,0,0);sleeping=1;issue(1,0,0);
  packet(6,0,64'hfeedf00dcafebabe,13,1);
  packet(6,0,64'hfeedf00dcafebabe,8);
  packet(6,1,64'hfeedf00dcafebabe);
  if(acks!=1)$fatal(1,"partial or incorrect restore committed");
  packet(6,0,64'hdeadbeef11223344);if(acks!=2 || last_load!=64'hdeadbeef11223344)$fatal;
  @(negedge clk);restored=1;sleeping=0;@(negedge clk);restored=0;
  packet(0,0,0);if(!rx[1][5]||rx[1][7])$fatal(1,"load done");
  packet(2,0,0);if(hold_core)$fatal(1,"resume");
  packet(1,0,0);packet(4,0,0);sleeping=1;issue(1,11,0);reset=1;repeat(4)@(negedge clk);
  if(hold_core || stream_done || selected)$fatal(1,"STOP");
  for(int mode=1;mode<=3;mode++)begin
    @(negedge clk);reset=0;paused=1;drained=1;sleeping=0;
    packet(1,0,0);packet(4,0,0);sleeping=1;issue(1,1,0);
    packet(6,1,64'(mode)<<48);packet(0,0,0);
    if(!rx[1][7] || !rx[1][2] || acks!=2)$fatal(1,"foreign CPU mode committed");
    reset=1;repeat(4)@(negedge clk);
  end
  $display("PASS FF3 state SPI pause, battery, save/load, CRC, exact word ACK, retry and STOP");$finish;
 end
endmodule
