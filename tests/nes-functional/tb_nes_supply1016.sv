`timescale 1ns/1ps
module tb_nes_supply1016;
 reg [4:0] drive_inputs=0;
 reg clk=0,nes=0,reset=1,active=0,cancel=0,first=0,writer=0,ret=0,reader=0,retired=0;
 reg ss=1,sck=0,mosi=0;
 wire miso,origin,bw;wire [8:0] rd;wire [31:0] q,bword;
 reg start_tile=0,done=0,accept=0,reply=0,capture=0,rowhit=0,fg=0,grant=0,spec=0,demand=0;
 reg [12:0] tag=0;reg [16:0] addr=0;reg [1:0] kind=0;
 reg [31:0] token=0;reg [7:0] units=0;reg k=0;
 reg [15:0] gen=1384;
 always #6 clk=~clk;always #23 nes=~nes;
 nes_supply1016 src(.clk(nes),.stop(reset||cancel),.origin_toggle(origin),.start_tile(start_tile),
 .done(done),.tag(tag),.kind(kind),.generation(gen),.accept_read(accept),.reply(reply),
 .capture_hit(capture),.row_hit(rowhit),.foreground(fg),.grant(grant),.spec_busy(spec),
 .demand(demand),.address(addr),.host_clk(clk),.rd(rd),.bank_we(bw),.bank_word(bword),.q(q));
 nes_screen_status151 status(.bw1016(bw),.word1016(bword),.origin1016(origin),.rd1016(rd),.q1016(q),.trace_cancel(cancel),
 .evt905(3'b0),.first905(first),.ret905(ret),.units905(units),.writer903(writer),.reader903(reader),
 .ready903(1'b0),.snap903(1'b0),.kind903(k),.token903(token),.clk(clk),.reset(reset),
 .active(active),.pawr_n(1'b1),.port_id(8'd0),.tr_head(1'b0),.tr_section(1'b0),
 .tr_retired(retired),.tr_data(8'd0),.tr_op(8'd3),.tr_gen(gen),.address(24'd0),
 .read_n(1'b1),.write_n(1'b1),.romsel_n(1'b1),.data_in(8'd0),.drive_inputs(drive_inputs),
 .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.miso(miso));
 task n;@(negedge nes);endtask
 task h;@(negedge clk);endtask
 task octet(input [7:0] tx,output [7:0] rx);
  for(integer i=7;i>=0;i--)begin mosi=tx[i];#190;sck=1;#95;rx[i]=miso;#95;sck=0;end
 endtask
 reg [7:0] data[32],b;
 task page(input integer p,input integer stop_byte);
  ss=0;#250;octet('h78,b);
  for(integer j=1;j<32;j++)begin
   if(j==stop_byte)cancel=1;
   octet(j==1?p:0,data[j]);
  end
  ss=1;#250;
 endtask
 integer fd;

 task sample(input integer delay_count,input integer run);
  fd=$fopen(run==0?"fast-pages.hex":"slow-pages.hex","w");
  h;first=1;h;first=0;repeat(8)n;
  for(integer t=0;t<15;t++)begin
   tag=100+t;kind=t>=4;start_tile=1;n;start_tile=0;n;
   addr={tag,4'b0011};accept=1;n;accept=0;
   if(t%3==0)begin
    demand=1;spec=1;
    if(t==3)repeat(delay_count)n;
    n;spec=0;fg=1;n;grant=1;n;grant=0;fg=0;demand=0;n;
   end
   capture=t%3==1;rowhit=t%3==2;reply=1;n;reply=0;capture=0;rowhit=0;n;n;
   done=1;n;done=0;n;
   if(t==3||t==12||t==14)begin
    h;writer=!writer;token=t==3?200:t==12?201:202;reader=t==12;
    k=t!=3;units=t==3?4:t==12?18:4;ret=1;h;ret=0;n;
   end
  end
  h;retired=1;h;retired=0;
  for(integer p=0;p<=19;p++)begin
   page(p==0?128:p-1,-1);
   if(data[31]!==8'ha5 || data[30]!=(p==0?128:p-1))$fatal(1,"header or echo");
   for(integer j=1;j<32;j++)$fwrite(fd,"%02x",data[j]);
   $fwrite(fd,"\n");
  end
  $fclose(fd);
 endtask
 initial begin
  repeat(5)h;reset=0;active=1;repeat(8)n;
  for(integer v=0;v<32;v++)begin
   h;drive_inputs=v;h;drive_inputs=~v;h;
   if(status.drive_sync[1]!==(!v[4]&&(v[3]!=v[2])&&(v[3]?v[1]:v[0])))$fatal(1,"boot observation");
  end
  sample(3,0);
  page(1,20);if(data[31]!==0)$fatal(1,"STOP");
  cancel=0;repeat(4)h;page(0,-1);if(data[31]!==0)$fatal(1,"stale capture");
  sample(32769,1);
  $display("PASS1016 two event traces, bank receipts, physical SPI, mid-page STOP and recovery");
  $finish;
 end
endmodule
