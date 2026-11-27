module cart1056_tb #(parameter MAPPER=3);
 reg clk=0,reset=1,wr=0,ce=0;
 reg [15:0] cpu;
 reg [7:0] din;
 reg [13:0] ppu;
 wire [24:0] pa;
 wire [21:0] ca,predict;
 wire [7:0] dout;
 wire allow,drive,irq;
 cart_top dut(.clk(clk),.ce(ce),.reset(reset),.prg_write(wr),.prg_ain(cpu),.prg_din(din),
  .prg_aout(pa),.prg_dout(dout),.prg_bus_write(drive),.prg_allow(allow),.irq(irq),
  .chr_ain_orig(ppu),.game148_hint_logic(ppu),.chr_aout(ca),.game148_hint_physical(predict),
  .game158_preview_write(wr));
 task tick;begin #2;clk=1;#2;clk=0;#1;end endtask
 task put(input [15:0] addr,input [7:0] v);begin cpu=addr;din=v;wr=1;ce=1;tick();wr=0;ce=0;end endtask
 integer stream,kind,address,value,reads=0,writes=0,i;
 string path;
 initial begin
  tick();reset=0;
  if(!$value$plusargs("trace=%s",path))$fatal(1,"missing reference");
  stream=$fopen(path,"r");if(!stream)$fatal;
  while($fscanf(stream,"%h %h %h",kind,address,value)==3)begin
   case(kind)
    0:begin put(address,value);writes++;end
    1:begin cpu=address;#1;if(!allow || pa!==value)$fatal(1,"PRG %h %h expected %h",cpu,pa,value);reads++;end
    2:begin ppu=address;#1;if(ca!==(22'h200000|value) || predict!==ca)$fatal(1,"CHR %h %h expected %h",ppu,ca,value);reads++;end
    3:begin ppu=address;#1;if(ca!==(22'h3a0000|value))$fatal(1,"NT %h %h expected %h",ppu,ca,value);reads++;end
   endcase
  end
  $fclose(stream);
  if(reads!=240 || writes==0)$fatal(1,"incomplete trace");
  if(MAPPER==7)begin
    for(i=0;i<16;i++)begin put(16'h8000,i|16);cpu=16'h8123;ppu=0;#1;
     if(pa!==((i<<15)|'h123) || ca!==22'h200000)$fatal;
     ppu=14'h2000;#1;if(ca!==22'h3a0400)$fatal;
    end
  end
  if(MAPPER==21)begin
   put('hf000,15);put('hf002,15);put('hf004,2);ce=1;
   repeat(113)tick();if(irq)$fatal;tick();if(!irq)$fatal;
   put('hf006,0);if(irq)$fatal;
  end
  if(MAPPER==5)begin
   put('h5104,2);put('h5c18,'h37);put('h5d18,'ha6);
   cpu='h5c18;tick();if(!drive || allow || dout!==8'h37)$fatal(1,"ExRAM");
   cpu='h5d18;tick();if(dout!==8'ha6)$fatal;
   put('h5104,3);put('h5c18,'hff);tick();if(dout!==8'h37)$fatal;
   put('h5100,1);put('h5115,'h80);cpu='h8321;#1;if(pa!=='h321)$fatal;
   put('h5115,'hc0);cpu='h8321;#1;if(pa!=='h80321)$fatal(1,"upper PRG alias");
  end
  reset=1;tick();$display("PASS mapper=%0d writes=%0d reference_addresses=%0d",MAPPER,writes,reads);$finish;
 end
endmodule
