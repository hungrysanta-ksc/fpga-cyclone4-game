`timescale 1ns/1ps
module screen141_cache_tb;
 reg clk=0,reset=1;always #5 clk=~clk;
 reg [21:0] address=22'h200001,reply_address=0;
 reg need=0,sample=0,response=0;reg[7:0] data=0;
 wire request,valid,fault;wire[21:0] requested;wire[7:0] value;wire[3:0] error;
 reg[24:0] cpu_address=25'h10000;reg cpu_need=0,cpu_sample=0;wire cpu_valid;wire[7:0] cpu_value;
 integer checks=0;
 nes_rom_early dut(.clk(clk),.reset(reset),.cpu_address_valid(cpu_need),.ppu_address_valid(need),.cpumem_addr(cpu_address),.cpumem_read(1'b0),.cpu_sample(cpu_sample),.ppumem_addr(address),.ppumem_read(need),.ppu_sample(sample),.cpu_data(cpu_value),.ppu_data(value),.cpu_valid(cpu_valid),.ppu_valid(valid),.rom_ready(1'b1),.rom_request(request),.rom_address(requested),.rom_response(response),.rom_error(1'b0),.rom_response_address(reply_address),.rom_data(data),.fault_trigger(),.fault_context(),.fault(fault),.error_code(error));
 task ck(input bit ok,input string name);checks++;if(!ok)$fatal(1,"CACHE141 %s",name);endtask
 task tick;@(posedge clk);#1;@(negedge clk);endtask
 task clear;reset=1;tick();reset=0;need=0;sample=0;response=0;cpu_need=0;cpu_sample=0;tick();endtask
 task fill(input[21:0] a,input[7:0] b);
  address=a;need=1;#1;ck(request&&!valid,"new address requests");tick();
  reply_address=a;data=b;response=1;#1;ck(valid&&value==b,"reply bypass");tick();response=0;#1;ck(valid&&value==b&&!request,"reply cached");
 endtask
 task hit(input[21:0] a,input[7:0] b);
  address=a;sample=1;need=1;#1;ck(valid&&value==b&&!request,"two-entry hit byte/tag");tick();ck(!fault,"cached deadline");sample=0;
 endtask
 task cpu_fill(input[24:0] a,input[7:0] b);
  cpu_address=a;cpu_need=1;#1;ck(request&&!cpu_valid,"CPU miss");tick();
  reply_address=a[21:0];data=b;response=1;#1;ck(cpu_valid&&cpu_value==b,"CPU reply bypass");tick();response=0;
 endtask
 task cpu_hit(input[24:0] a,input[7:0] b);
  cpu_address=a;cpu_need=1;cpu_sample=1;#1;ck(cpu_valid&&cpu_value==b&&!request,"CPU indexed byte/tag");tick();ck(!fault,"CPU cached deadline");cpu_sample=0;
 endtask
 initial begin
  clear();fill(22'h201ff2,8'ha2);fill(22'h201ffa,8'hb7);
  repeat(4)begin hit(22'h201ff2,8'ha2);hit(22'h201ffa,8'hb7);end
  fill(22'h200012,8'hc9);hit(22'h201ffa,8'hb7);
  address=22'h201ff2;#1;ck(!valid&&request,"oldest entry evicted");need=0;
  clear();address=22'h201ffa;need=1;#1;ck(!valid&&request,"reset invalidates both");tick();
  response=1;reply_address=22'h201ff2;data=8'hee;tick();ck(fault&&error==4,"wrong tag rejected");
  clear();fill(22'h200001,8'h11);address=22'h208001;#1;ck(!valid&&!request,"outside ROM geometry never aliases");
  clear();address=22'h200002;need=1;sample=1;tick();ck(fault&&error==2,"uncached missed deadline still fails");
  clear();for(integer i=0;i<8;i++)cpu_fill(25'he180+i,8'h80+i);
  for(integer i=0;i<8;i++)cpu_hit(25'he180+i,8'h80+i);
  cpu_fill(25'he188,8'h55);cpu_hit(25'he188,8'h55);
  cpu_address=25'he180;#1;ck(!cpu_valid&&request,"CPU indexed conflict rejects old tag");
  clear();cpu_address=25'he188;cpu_need=1;#1;ck(!cpu_valid&&request,"CPU reset invalidates line");
  clear();cpu_address=25'he18f;cpu_need=1;cpu_sample=1;tick();ck(fault&&error==1,"uncached CPU deadline still fails");
  $display("PASS141 CACHE checks=%0d",checks);$finish;
 end
endmodule
