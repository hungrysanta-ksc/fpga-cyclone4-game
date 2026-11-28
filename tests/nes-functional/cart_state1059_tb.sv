module cart_state1059_tb;
 reg clk=0,reset=1,ce=0,wr=0,load=0,we=0,active=0,ram_we=0;
 reg [15:0] cpu=0;
 reg [7:0] data=0;
 reg [9:0] regno=32;
 reg [12:0] address=0;
 reg [63:0] restore_word=0,held[0:1];
 wire [63:0] q;
 wire [7:0] ram_q;
 wire [24:0] prg;
 always #5 clk=!clk;
 cart_top dut(.clk(clk),.ce(ce),.reset(reset),.prg_ain(cpu),.prg_write(wr),.prg_din(data),
  .chr_ain_orig(14'd0),.game148_hint_logic(14'd0),.game158_preview_write(1'b0),.prg_aout(prg),
  .SaveStateBus_Din(restore_word),.SaveStateBus_Adr(regno),.SaveStateBus_load(load),
  .SaveStateBus_wren(we),.SaveStateBus_rst(reset),.SaveStateBus_Dout(q),
  .Savestate_MAPRAMactive(active),.Savestate_MAPRAMAddr(address),.Savestate_MAPRAMWrEn(ram_we),
  .Savestate_MAPRAMRdEn(!ram_we),.Savestate_MAPRAMWriteData(data),.Savestate_MAPRAMReadData(ram_q));
 task tick;begin @(posedge clk);#1;end endtask
 task put(input [15:0] a,input [7:0] b);
   begin cpu=a;data=b;wr=1;ce=1;tick();wr=0;ce=0;end
 endtask
 task verify_regs(input integer n);
   begin regno=32+n;
    for(integer j=0;j<8;j++)begin address=j;#1;
     if(q!=={56'd0,held[n][8*j+:8]})$fatal(1,"mapper word %0d lane %0d read %h",n,j,q);
    end
   end
 endtask
 integer mapper,words;
 initial begin
  if(!$value$plusargs("mapper=%d",mapper))$fatal;
  words=mapper==21?2:1;
  tick();reset=0;
  case(mapper)
   5:begin
    put('h5100,1);put('h5102,2);put('h5103,1);put('h5104,2);put('h5105,'he4);
    put('h5114,'h83);put('h5115,'h8b);put('h5116,'h95);put('h5117,'hfa);
    held[0]=64'h0000fa958b83e499;
    for(integer k=0;k<1024;k++)put('h5c00+k,(k*37)^(k>>8));
   end
   7:begin put('h8000,'h1b);held[0]='h1b;end
   21:begin
    put('h8000,9);put('ha000,7);put('h9000,2);put('h9004,2);
    put('hb000,6);put('hb002,3);put('hf000,1);put('hf002,5);
    held[0]=64'd9|(64'd7<<5)|(64'd1<<10)|(64'd2<<11)|(64'h51<<13)|(64'd341<<29);
    held[1]='h36;
   end
  endcase
  active=1;
  for(integer i=0;i<words;i++)verify_regs(i);
  if(mapper==5)for(integer i=0;i<1024;i++)begin address=i;tick();if(ram_q!==8'((i*37)^(i>>8)))$fatal(1,"exram %d",i);end
  reset=1;tick();reset=0;load=1;we=1;
  for(integer i=0;i<words;i++)begin regno=32+i;restore_word=held[i];tick();end
  we=0;
  if(mapper==5)begin
   ram_we=1;for(integer i=0;i<1024;i++)begin address=i;data=(i*17)^(i>>6);tick();end
   ram_we=0;
   for(integer i=0;i<1024;i++)begin address=i;tick();if(ram_q!==8'((i*17)^(i>>6)))$fatal(1,"restore %d",i);end
  end
  load=0;
  for(integer i=0;i<words;i++)verify_regs(i);
  $display("PASS mapper %0d capture, reset and restore",mapper);$finish;
 end
endmodule
