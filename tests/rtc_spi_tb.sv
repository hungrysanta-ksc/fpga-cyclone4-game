`timescale 1ns/1ps
module tb;
reg clk=0,sck=0,mosi=0,ss=1,reset=1;always #14.900662 clk=~clk;
wire miso,cr,pr,em,sm;wire[7:0]cd,pd,si;wire[31:0]bc;wire[2:0]bits;
gbc_spi spi(clk,sck,mosi,miso,ss,cr,pr,cd,pd,em,sm,si,bc,bits);
wire rr,wr,done;wire[7:0]wd,rd;wire[23:0]address,mask;wire[15:0]features;
wire[16:0]ram_mask;wire[3:0]mapper;reg ready_level=1;
always @(posedge clk)begin if(rr||wr)ready_level<=0;else if(done)ready_level<=1;end
gbc_mcu_cmd dec(clk,cr,pr,cd,pd,bc,ready_level,rd,rr,wr,wd,si,address,mask,features,ram_mask,mapper);
reg safe=1,latch_write=0;reg[7:0]cartdata=0;wire[7:0]cartread;wire[28:0]statebits;wire dirty;
gbc_mbc3_rtc rtc(clk,reset,features[15],mapper==11,!features[15],latch_write,cartdata,1'b0,4'd8,cartread,safe,rr,wr,address[3:0],wd,done,rd,1'b0,64'b0,statebits,dirty,);
reg[7:0]reply;integer j;
task transfer(input[7:0]value);integer b;begin reply=0;for(b=7;b>=0;b=b-1)begin mosi=value[b];#80;reply={reply[6:0],miso};sck=1;#80;sck=0;end #1200;end endtask
task begin_msg;begin ss=0;#200;end endtask
task end_msg;begin ss=1;#400;end endtask
task setaddr(input[23:0]a);begin begin_msg();transfer(0);transfer(a[23:16]);transfer(a[15:8]);transfer(a[7:0]);end_msg();end endtask
task get(input[23:0]a,input[7:0]v);begin setaddr(a);begin_msg();transfer('h80);wait(ready_level);transfer(0);if(reply!==v)$fatal(1,"SPI RTC %h got %h expected %h",a,reply,v);end_msg();end endtask
initial begin
 #200;reset=0;#200;begin_msg();transfer('h3b);end_msg();
 setaddr('hf20000);begin_msg();transfer('h98);transfer(8);transfer(4);transfer(0);transfer(0);transfer(64);end_msg();
 setaddr('hf2000e);begin_msg();transfer('h98);transfer(0);end_msg();
 get('hf20000,8);get('hf20001,4);get('hf20004,64);get('hf20008,8);get('hf2000c,64);
 begin_msg();transfer('hef);transfer('h80);transfer(0);end_msg();
 safe=0;get('hf20000,255);if(cartread!==8)$fatal(1,"unsafe MCU read corrupted game bus");
 get('hf2000f,255);if(cartread!==8)$fatal(1,"speculative release read corrupted game bus");
 safe=1;get('hf20000,8);get('hf20008,8);
 setaddr('hf20000);begin_msg();transfer('h98);transfer(55);end_msg();get('hf20000,8);
 $display("PASS actual SPI RTC import readback RUN-write guard unsafe-read guard and repeated release read");$finish;
end
initial begin #10000000;$fatal(1,"timeout");end
endmodule
