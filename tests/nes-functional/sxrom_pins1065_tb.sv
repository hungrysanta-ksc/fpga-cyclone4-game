module sxrom_pins1065_tb;
 reg clk=0,reset=1,ce=0,wr=0;
 reg [15:0] addr=0;
 reg [13:0] ppu=0;
 reg [7:0] data=0;
 wire [25:0] state_out;
 wire [17:0] inner;
 wire [18:0] prg;
 wire [14:0] battery;
 wire enabled;
 nes_mmc1_1063 dut(.clk(clk),.reset(reset),.cpu_ce(ce),.cpu_write(wr),.preview_write(1'b0),
  .cpu_address(addr),.cpu_data(data),.ppu_address(ppu),.lookahead(ppu),
  .restore(1'b0),.restored_state(26'd0),.saved_state(state_out),.prg_address(inner),.ram_selected(enabled));
 nes_sxrom_address1065 pins(state_out[4],ppu[12],state_out[9:5],state_out[14:10],inner,addr[12:0],prg,battery);
 task tick; #2;clk=1;#2;clk=0;#1;endtask
 task serial(input int address,value);
  for(int i=0;i<5;i++)begin ce=1;wr=0;tick();addr=address;data=value>>i;wr=1;tick();end
 endtask
 int kind,address,value,stamp,last=-10,fd,roms=0,rams=0,halves=0,banks=0,writes=0;
 string file;
 initial begin
  tick();reset=0;ce=1;
  if(!$value$plusargs("trace=%s",file))$fatal;
  fd=$fopen(file,"r");if(!fd)$fatal;
  while($fscanf(fd,"%h %h %h",kind,address,value)==3)case(kind)
   0:begin
    if($fscanf(fd,"%h",stamp)!=1 || stamp<=last)$fatal;
    if(stamp!=last+1)begin wr=0;tick();end
    addr=address;data=value;wr=1;tick();last=stamp;writes++;
   end
   1:begin addr=address;#1;if(prg!==value)$fatal(1,"PRG %h %h expected %h",addr,prg,value);
    halves|=1<<prg[18];roms++;end
   4:begin addr=address;#1;if(!enabled || battery!==value)$fatal(1,"battery %h expected %h",battery,value);
    banks|=1<<battery[14:13];rams++;end
   default:$fatal;
  endcase
  $fclose(fd);if(roms!=96 || rams==0 || writes==0)$fatal;
  // The physical PPU A12 pin selects the CHR register in 4 KiB mode.
  serial('h8000,'h1c);serial('ha000,'h04);serial('hc000,'h18);
  addr='h6123;ppu=0;#1;if(prg[18]!==0 || battery!==15'h2123)$fatal;
  ppu='h1000;#1;if(prg[18]!==1 || battery!==15'h4123)$fatal;
  serial('h8000,'h0c);addr='h6123;#1;if(prg[18]!==0 || battery!==15'h2123)$fatal;
  $display("PASS SXROM writes=%0d ROM=%0d RAM=%0d halves=%h banks=%h",writes,roms,rams,halves,banks);$finish;
 end
endmodule
