`timescale 1ns/1ps
module kirby1035_export_tb;
 reg clk=0,h=0,reset=1,stop=0,prime=1,capture=0,owned=0,valid=0;
 reg priming_commit=0,retire=0,drained=1,closed=0;
 reg [15:0] gen=16'hffff;
 always #23.281 clk=~clk;
 always #5.952 h=~h;
 `include "spi200_bus.svh"
 wire [3:0] error;
 wire spi_fault;
 wire cleared=reset||stop;
 wire release_export,release_frame,lease,allow_retire,allow_export,lease_fault;
 wire [15:0] previous;
 nes_capture_lease201 ownership(.clk(clk),.reset(reset),.stop(stop),.capture_begin(capture),
  .frame_owned(owned),.geometry_valid(valid),.frame_generation(gen),.export_release(priming_commit||release_export),
  .export_error(error),.source_ready(1'b1),.source_is_rom(1'b1),.source_writing(1'b0),.live_epoch(32'd15),
  .reader_drained(drained),.retire_commit(retire),.retire_generation(16'd0),.release_frame(release_frame),
  .lease_valid(lease),.retire_permitted(allow_retire),.export_permitted(allow_export),
  .captured_generation(previous),.fault(lease_fault));
 wire export_permitted204=allow_export, lease204=lease, plan_closed204=closed;
 wire native_geometry_valid=valid, direct_nes_fault204=prime,reader_drained204=drained;
 wire [16:0] native_ack_data;
 `include "gate1035.svh"
 wire ask,tx,tx_ready,rx,rx_ready,prepared,accepted,ack_nes;
 wire [15:0] ack_gen;
 wire [95:0] word_tx,word_rx;

 wire [2:0] kind;
 wire [12:0] addr;
 reg response=0;
 reg [63:0] memory[0:16383],value;
 always @(posedge clk)begin response<=ask;if(ask)value<=memory[kind*2048+addr];end
 nes_native_export203 exporter(.clk(clk),.reset(cleared),.enable(run_gate),.start_permitted(start_gate),
  .discard_permitted(allow_export),.frame_owned(owned),.geometry_valid(valid),.frame_generation(gen),
  .patch_count(3'd2),.row_count(8'd224),.object_count(8'd18),.exception_count(8'd0),
  .group_count(6'd28),.palette_count(6'd1),.release_frame(release_export),
  .query(ask),.query_kind(kind),.query_index(addr),.response(response),.hit(response),.data(value),
  .tx_valid(tx),.tx_ready(tx_ready),.tx_data(word_tx),.ack_valid(ack_nes),.ack_accept(commit_gate),
  .ack_generation(native_ack_data[15:0]),.error(error));
 nes_native_mailbox165 records(.src_clk(clk),.dst_clk(h),.reset(cleared),.src_valid(tx),.src_ready(tx_ready),
  .src_data(word_tx),.dst_valid(rx),.dst_ready(rx_ready),.dst_data(word_rx));
 wire ack_ready;
`ifdef INTERVAL1035
 reg [14:0] phase_clock=0;
 always @(posedge h)phase_clock<=phase_clock+1'b1;
 reg release_source=0,start_source=0;
 always @(posedge clk)begin release_source<=!reset && release_frame;start_source<=capture&&!cleared;end
`endif
 nes_native_mailbox165 #(.WIDTH(17)) acks(.src_clk(h),.dst_clk(clk),.reset(cleared),.src_valid(prepared),
  .src_ready(ack_ready),.src_data({accepted,ack_gen}),.dst_valid(ack_nes),.dst_ready(1'b1),.dst_data(native_ack_data));
 nes_native_spi165 spi(.clk(h),.reset(cleared),.SPI_SS(ss197),.SPI_SCK(sck197),.SPI_MOSI(mosi197),
`ifdef INTERVAL1035
  .phase(phase_clock[14]),.source_release(release_source),.source_start(start_source),
`endif
  .selected(selected197),.miso(miso197),.record_valid(rx),.record_ready(rx_ready),.record_data(word_rx),
  .ack_valid(prepared),.ack_ready(ack_ready),.ack_accept(accepted),.ack_generation(ack_gen),.fault(spi_fault));
 reg [7:0] golden[0:8191],got;
 integer lengths[0:17],phase,hold_us,capture_late,mode,qfile,kind_in,addr_in;
 reg [63:0] val_in;
 realtime released_at,captured_at,geometry_at,first_at,deadline;
 task n; @(negedge clk);endtask
 task status(input byte op,input int offset,input bit arg);
  reg [7:0] req[0:7];reg [7:0] crc;
  req[0]=op;req[1]=0;req[2]=offset>>8;req[3]=offset;req[4]=arg;req[5]=~req[4];req[6]=0;req[7]='ha5;
  for(int j=0;j<6;j++)req[6]=crc8_197(req[6],req[j]);
  begin197();for(int j=0;j<8;j++)byte197(req[j],rx197[j]);end197();
  crc=0;for(int j=1;j<7;j++)crc=crc8_197(crc,rx197[j]);
  if(rx197[1]!==8'hd6 || rx197[7]!==crc || rx197[2][7]!==0)$fatal(1,"bad status");
 endtask
 task read_block(input int seq);
`ifdef INTERVAL1035
  integer expected_age,observed;
`endif
  wait(spi.available);
  status('hd0,0,0);
  if({rx197[3],rx197[4]}!==seq || {rx197[5],rx197[6]}!==lengths[seq]-2 || !rx197[2][0])$fatal(1,"bad token or length %d",seq);
  begin197();byte197('hd1,got);
  for(int j=0;j<lengths[seq];j++)begin
   byte197(0,got); if(got!==golden[256*seq+j])$fatal(1,"D1 payload/CRC %d %d",seq,j);
  end
  end197();status('hd2,seq,0);
`ifdef INTERVAL1035
  if(seq==1 || seq==2)begin
   expected_age=$rtoi((seq==1?captured_at-released_at:first_at-captured_at)/(32768*11.904));
   if(expected_age>127)expected_age=127;
   observed=rx197[5]>>1;
   if($isunknown(rx197[5]) || observed<expected_age-1 || observed>expected_age+1)
     $fatal(1,"wrong input interval block=%d actual=%d expected=%d",seq,observed,expected_age);
  end
`endif
 endtask
 always @(posedge clk) if(!cleared && !prime && (spi_fault || (mode!=2 && (error!=0 || lease_fault))))$fatal(1,"lease/SPI/export error");
 initial begin
  if(!$value$plusargs("PHASE=%d",phase)||!$value$plusargs("HOLD=%d",hold_us)||
     !$value$plusargs("LATE=%d",capture_late)||!$value$plusargs("MODE=%d",mode))$fatal;
  $readmemh("golden.hex",golden);$readmemh("lengths.hex",lengths);
  qfile=$fopen("frame.query","r");
  while($fscanf(qfile,"%d %d %h",kind_in,addr_in,val_in)==3)memory[kind_in*2048+addr_in]=val_in;
  $fclose(qfile);
  repeat(8)n;reset=0;repeat(8)n;
  capture=1;n;capture=0;gen=0;owned=1;valid=1;priming_commit=1;n;
  released_at=$realtime;priming_commit=0;valid=0;owned=0;prime=0;
  if(!lease||previous!=0||allow_export)$fatal(1,"initial lease");
  deadline=$realtime+hold_us*1000;
  fork
   begin
    #(hold_us*1000);n;closed=1;
   end
   begin
    if(capture_late) #(hold_us*1000);
`ifdef INTERVAL1035
    #1700000;
`endif
    repeat(phase+2)n; capture=1;captured_at=$realtime;n;capture=0;gen=1;
`ifdef INTERVAL1035
    #3200000;
`endif
    repeat(10)n;owned=1;valid=1;geometry_at=$realtime;
    wait(spi.available);first_at=$realtime;
    if(previous!==0 || allow_export || release_export)$fatal(1,"early ownership change");
    if(mode==1)begin stop=1;repeat(8)n;stop=0;owned=0;valid=0;repeat(8)n;
     if(spi.available||lease||spi_fault||tx||rx||prepared)$fatal(1,"STOP retained input");
     $display("PASS1035 STOP");$finish;
    end
    for(int b=0;b<17;b++)read_block(b);
    if(mode==2)begin
     status('hd3,1,1);repeat(32)n;
     if(error!=6 || previous!=0 || lease || !lease_fault)$fatal(1,"premature D3");
     stop=1;repeat(8)n;$display("PASS1035 premature D3 rejected");$finish;
    end
    wait(closed);n;retire=1;n;retire=0;
    if(!allow_export||lease||lease_fault)$fatal(1,"retirement");
    status('hd3,1,1); read_block(17);
    if(!lease||previous!=1||error||spi_fault)$fatal(1,"commit");
    stop=1;repeat(8)n;if(lease||spi.available)$fatal(1,"STOP");
    $display("PASS1035 phase=%0d hold_us=%0d late=%0d release_ns=%.1f capture_ns=%.1f geometry_ns=%.1f offer_ns=%.1f",phase,hold_us,capture_late,released_at,captured_at,geometry_at,first_at);$finish;
   end
  join
 end
 initial #60000000 $fatal(1,"timeout");
endmodule
