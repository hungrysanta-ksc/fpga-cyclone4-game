// Compare every bus bit of boot SPI73 with the shipped Kirby endpoint.
`timescale 1ns/1ps
module tb_nes_kirby1027_status;
 reg clk=0,reset=1,active=1,rd=1,wr=1,romsel=1,drive=0;
 always #6 clk=!clk;
 reg ss=1,sck=0,mosi=0;
 reg [23:0] address=0;
 reg [7:0] din=0;
 wire old_sel,new_sel,old_miso,new_miso,old_write,new_write;
 `define PORTS .clk(clk),.reset(reset),.active(active),.pawr_n(1'b1),.port_id(8'd0), \
 .tr_head(1'b0),.tr_section(1'b0),.tr_retired(1'b0),.tr_data(8'd0),.tr_op(8'd0),.tr_gen(16'd0), \
 .address(address),.read_n(rd),.write_n(wr),.romsel_n(romsel),.data_in(din),.bus_drive(drive), \
 .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.trace_cancel(1'b0),.evt905(3'd0),.first905(1'b0), \
 .ret905(1'b0),.units905(8'd0),.writer903(1'b0),.reader903(1'b0),.ready903(1'b0),.snap903(1'b0),.kind903(1'b0),.token903(32'd0)
 nes_screen_status151_old a(`PORTS,.receive_write(old_write),.selected(old_sel),.miso(old_miso));
 wire [31:0] synchronized_bus;
 nes_screen_status151 b(`PORTS,.edge1027(2'd0),.sampled_bus(synchronized_bus),.receive_write(new_write),.selected(new_sel),.miso(new_miso));
 reg session_reset=1,stop=0;
 wire [63:0] legacy_bus,current_bus;
 `define BUS .clk(clk),.reset(session_reset),.active(!session_reset),.stop(stop),.fault(1'b0),.address(address), \
 .read_n(rd),.write_n(wr),.romsel_n(romsel),.data_in(din),.packet_ready(1'b1),.packet_length(9'd224),.packet_data(8'h37)
 `define OUT(v) .tr_head(v[0]),.tr_section(v[1]),.tr_data(v[9:2]),.data_out(v[17:10]),.oe_n(v[18]),.dir(v[19]), \
 .packet_address(v[27:20]),.map_progress(v[28]),.ack_write(v[29]),.ack_index(v[33:30]),.ack_byte(v[41:34]), \
 .ack_publish(v[42]),.pad_commit(v[43]),.pad_buttons(v[59:44])
 nes_sink_bus165_old old_sink(`BUS,`OUT(legacy_bus));
 nes_sink_bus165 new_sink(`BUS,`OUT(current_bus),.sampled_bus(synchronized_bus));
 integer samples=0,publishes=0,progress_events=0;
 always @(negedge clk)if(!reset)begin
  if({old_sink.address_sync,old_sink.data_sync,old_sink.address_previous,old_sink.data_previous,legacy_bus[59:0]}
     !=={new_sink.address_sync,new_sink.data_sync,new_sink.address_previous,new_sink.data_previous,current_bus[59:0]})
   $fatal(1,"sink sample/ROM/data/ACK mismatch at sample %d",samples);
  samples++;if(current_bus[42])publishes++;if(current_bus[28])progress_events++;
 end
 task h;repeat(6)@(negedge clk);endtask
 task send(input bit v);
  mosi=v;h;sck=1;h;sck=0;h;
 endtask
 integer bits=0;
 reg [55:0] payload;
 task start73;
  ss=0;h;
  for(integer i=7;i>=0;i--)send((8'h73>>i)&1);
  if(!new_sel || !old_sel || new_miso!==1'b1)$fatal(1,"SPI73 opcode/header");
  payload=b.snapshot;
 endtask
 task read_bits(input integer count);
  for(integer i=0;i<count;i++)begin
   if(!old_sel || !new_sel || old_miso!==new_miso || new_miso!==(i<56?payload[55-i]:1'b0))
    $fatal(1,"SPI73 bit %0d got=%b old=%b",i,new_miso,old_miso);
   bits++;send(i%2);
  end
 endtask
 task stage(input [23:0] addr,input [7:0] value);
  address=addr;din=value;wr=0;h;h;wr=1;h;
 endtask
 initial begin
  h;reset=0;h;session_reset=0;h;ss=0;h;send(0);send(1);ss=1;h;
  stage(24'h007000,8'h36);stage(24'h007001,8'ha5);
  start73();
  if(payload[55:32]!==24'he636a5)$fatal(1,"test setup");
  // Change the live state and frame count while the selected reply is frozen.
  stage(24'h007000,8'd6);drive=1;read_bits(265);ss=1;h;
  start73();if(payload[47:40]!=6 || payload[23:8]!=1)$fatal(1,"stale reply");
  read_bits(17);session_reset=1;reset=1;h;ss=1;h;reset=0;h;session_reset=0;h;
  start73();read_bits(64);ss=1;h;
  if(new_sel || old_sel || new_write!==old_write)$fatal;
  stage(24'h00601c,8'ha5);stage(24'h00601d,8'ha5);stop=1;stage(24'h00601d,8'ha5);stop=0;
  for(integer i=0;i<4096;i++)begin
   case(i%8)
    0:address=24'h008000+(i%5056);1:address=24'h00fffc+(i%4);
    2:address=24'h400000+(i%256);3:address=24'h006010+(i%14);
    default:address=$urandom;
   endcase
   din=$urandom;rd=i[2];wr=!rd;romsel=i[5];
   #1;session_reset=(i%59==0);@(negedge clk);
  end
  if(publishes==0 || progress_events!=1)$fatal(1,"ACK or STOP coverage");
  $display("PASS1027_BUS %0d observed clocks, session resets, ROM, packet, ACK and STOP",samples);
  $display("PASS1027_STATUS %0d SPI73 bits, partial request/reset, live stage and frame change",bits);
  $finish;
 end
endmodule
