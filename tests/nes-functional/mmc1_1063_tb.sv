module mmc1_1063_tb;
 reg clk=0, reset=1, ce=0, wr=0, preview=0, restore=0;
 reg [25:0] state_in=0;
 reg [15:0] cpu=0;
 reg [7:0] data=0;
 reg [13:0] ppu=0;
 wire [17:0] prg;
 wire [12:0] chr, next_chr;
 wire nt, ram_ok;
 wire [25:0] state_out;
 nes_mmc1_1063 dut(clk,reset,ce,wr,preview,cpu,data,ppu,ppu,restore,state_in,state_out,prg,chr,next_chr,nt,ram_ok);
 task tick; #2;clk=1;#2;clk=0;#1; endtask
 task idle; ce=1;wr=0;preview=0;tick(); endtask
 task put(input int addr,value);
   cpu=addr;data=value;ce=1;wr=1;preview=1;tick();wr=0;preview=0;
 endtask
 task serial(input int addr,value);
   for(int i=0;i<5;i++)begin idle();put(addr,(value>>i)&1);end
 endtask
 int fd,kind,addr,value,stamp,last=-10,reads=0,writes=0;
 string path;
 reg [25:0] snap;
 initial begin
   tick();reset=0;
   if(!$value$plusargs("trace=%s",path))$fatal;
   fd=$fopen(path,"r");if(!fd)$fatal;
   while($fscanf(fd,"%h %h %h",kind,addr,value)==3)begin
     case(kind)
     0:begin
       if($fscanf(fd,"%h",stamp)!=1)$fatal;
       if(stamp<=last)$fatal;
       if(stamp-last!=1)idle();
       put(addr,value); last=stamp;writes++;
     end
     1:begin cpu=addr;#1;if(prg!==value)$fatal(1,"PRG %h %h != %h",cpu,prg,value);reads++;end
     2:begin ppu=addr;#1;if(chr!==value || next_chr!==chr)$fatal(1,"CHR %h %h != %h",ppu,chr,value);reads++;end
     3:begin ppu=addr;#1;if({nt,ppu[9:0]}!==value)$fatal(1,"NT %h %b != %h",ppu,nt,value);reads++;end
     default:$fatal;
     endcase
   end
   $fclose(fd);
   if(reads!=240 || !writes)$fatal;
   reset=1;tick();reset=0;
   serial('h8000,5'h1c);
   idle();put('ha000,1);put('ha000,0); // consecutive write is ignored
   idle();put('ha000,0);snap=state_out;
   idle();put('ha000,'h80);
   restore=1;state_in=snap;tick();restore=0;
   idle();put('ha000,0);idle();put('ha000,0);idle();
   cpu='ha000;ppu=0;data=0;preview=1;#1;
   if(next_chr!==13'h1000 || chr!==0)$fatal(1,"fifth write lookahead after restore");
   put('ha000,0);#1;if(chr!==13'h1000)$fatal;
   serial('he000,'h12);cpu='h6000;#1;if(ram_ok)$fatal;
   serial('he000,2);cpu='h6000;#1;if(!ram_ok)$fatal;
   for(int mode=0;mode<4;mode++)for(int bank=0;bank<16;bank++)begin
     serial('h8000,mode<<2);serial('he000,bank);
     for(int half=0;half<2;half++)begin
       cpu='h8123+(half<<14);#1;
       value=mode<2 ? ((bank&14)+half) : mode==2 ? (half?bank:0) : (half?15:bank);
       if(prg!==((value<<14)+'h123))$fatal(1,"PRG mode/bank");
     end
   end
   $display("PASS MMC1 writes=%0d reference_addresses=%0d",writes,reads);$finish;
 end
endmodule
