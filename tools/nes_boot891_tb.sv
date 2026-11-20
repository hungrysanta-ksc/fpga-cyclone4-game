`timescale 1ns/1ps
module nes_boot891_tb;
 reg clk=0, session=0, reset_request=1;
 always #5.952 clk=~clk;
 reg [23:0] address=0;
 reg rd=1,wr=1,sel=1,ss=1,sck=0,mosi=0;
 reg [7:0] write_data=0;
 wire [7:0] data;
 assign data=wr?8'hzz:write_data;
 wire oe,dir,miso;
 fxpak_nes_screen137_top dut(.CLKIN(1'b0),.SNES_SYSCLK(1'b0),.SNES_ADDR_IN(address),
  .SNES_READ_IN(rd),.SNES_WRITE_IN(wr),.SNES_ROMSEL_IN(sel),.SNES_DATA(data),
  .SNES_DATABUS_OE(oe),.SNES_DATABUS_DIR(dir),.SPI_SS(ss),.SPI_SCK(sck),
  .SPI_MOSI(mosi),.SPI_MISO(miso));
 reg [7:0] expected[0:5119];
 task automatic ticks(input integer n);
  repeat(n) @(negedge clk);
 endtask
 task automatic spi(input [7:0] op,input integer len,output reg [63:0] reply);
  reg [7:0] send_byte; reply=0; ss=0; ticks(6);
  for(int i=0;i<len;i++)begin
   send_byte=i==0?op:0;
   for(int bitpos=7;bitpos>=0;bitpos--)begin
    mosi=send_byte[bitpos]; ticks(4); sck=1; ticks(4);
    if(i<8)reply={reply[62:0],miso};
    sck=0;ticks(4);
   end
  end
  ss=1;ticks(8);
 endtask
 task automatic fetch(input [23:0] addr,output reg [7:0] value,output bit drove);
  address=addr;sel=0;rd=0; #118;
  drove=(oe===0 && dir===1);
  value=data;
  if(!drove && data!==8'hzz)$fatal(1,"contended read addr=%h data=%h",addr,data);
  rd=1;sel=1;#1;
  if(data!==8'hzz)$fatal(1,"drive after release");
  #24;
 endtask
 task automatic first_write(input [7:0] v);
  address=24'h007000;write_data=v;wr=0;#118;wr=1;#60;
 endtask
 reg [63:0] reply;
 reg [7:0] lo,hi,opcode,ord,stage,flags;bit dl,dh,df;
 integer ph,scenario,admit;
`ifdef COMPACT891
 reg [23:0] prior_address=0;
 always @(posedge clk or posedge reset_request)begin
  if(reset_request) prior_address<=0;
  else begin
   if(dut.screen_status.was_stage!==(prior_address==24'h007000) ||
      dut.screen_status.was_error!==(prior_address==24'h007001) ||
      dut.screen_status.addr_stable!==(prior_address==dut.screen_status.addr_sync))
    $fatal(1,"address history differs from full-width register");
   prior_address<=dut.screen_status.addr_sync;
  end
 end
`endif
 initial begin
  $readmemh("sink-program.hex",expected);
  // Replace only the session/clock boundary; the actual top resolves both
  // data owners and the bus pins, bridge, ROM, SPI73 and write observer.
  force dut.host_clk=clk;
  force dut.host_locked=1;
  force dut.power_reset=reset_request;
  force dut.run_enable=session;
  force dut.core_reset=!session;
  for(ph=0;ph<4;ph++) for(scenario=0;scenario<7;scenario++)begin
   address=0;rd=1;wr=1;sel=1;session=0;reset_request=1;ticks(12);
   reset_request=0;ticks(12);
   spi(8'he0,20,reply);
`ifdef WITNESS891
   if(dut.screen_status.boot_armed!==1)$fatal(1,"first E0 not observed");
`else
   if(dut.screen_status.boot_e0!==1)$fatal(1,"first E0 not observed");
`endif
   // 0: ready before vector. 1: active only after both vector reads.
   // 2: between vector bytes. 3: early bus activity, then real vector.
   // 4: good fetches without a write. 5: good fetches then lost ownership at write.
   if(scenario==3)fetch(24'h00fffc,lo,dl);
   if(scenario!=1 && scenario!=2)begin session=1;ticks(20);end
   @(negedge clk);#(1+3*ph);
   fetch(24'h00fffc,lo,dl);
   if(scenario==2)begin session=1;ticks(20);end
   if(scenario==6)begin
    // Inject an incorrect resolved byte only while the high-vector strobe is active.
    address=24'h00fffd;sel=0;rd=0;force dut.SNES_DATA=8'h81;#118;
    dh=oe===0 && dir===1;hi=data;release dut.SNES_DATA;rd=1;sel=1;#25;
    if(hi!==8'h81 || !dh)$fatal(1,"high-byte injection failed");
   end else fetch(24'h00fffd,hi,dh);
   if(scenario==1)begin session=1;ticks(20);end
   spi(8'he0,20,reply);
   if(reply[55:48]!==8'hf7)$fatal(1,"missing post-release F7 %h",reply);
   admit=0;opcode=0;df=0;
   if(dl && dh && scenario!=6)begin
    if({hi,lo}!==16'h8000)$fatal(1,"wrong vector");
    // Sequential ROM reads through the first stage instruction. This is
    // a pin-level byte check, not instruction execution by a second CPU.
    for(int off=0;off<39;off++)begin
     fetch(24'h008000+off,opcode,df);
     if(!df || opcode!==expected[off])$fatal(1,"bad ROM byte %d",off);
    end
    if(scenario==5)begin session=0;ticks(12);end
    if(scenario!=4)begin first_write(1);admit=dut.screen_status.stage==1;end
    if(scenario==5)begin session=1;ticks(20);end
   end
   spi(8'h73,8,reply);
   if(reply[55:48]!==8'he6 || reply[7:0]!==3)$fatal(1,"bad status %h",reply);
   ord=dut.screen_status.boot_order;stage=reply[47:40];flags=reply[31:24];
   if(dl!==(scenario!=1 && scenario!=2) || dh!==(scenario!=1))$fatal(1,"vector drive mismatch");
   if(stage!==((scenario==0 || scenario==3)?1:0))$fatal(1,"stage=%d",stage);
   if(stage==0 && reply[39:32]!==ord)$fatal(1,"boot telemetry mismatch");
`ifdef WITNESS891
   case(scenario)
    0,3,5: if(ord!==8'h6f)$fatal(1,"first write witness %h",ord);
    1: if(ord!==8'h03 || flags[2:0]!==0)$fatal(1,"no drive %h",ord);
    2: if(ord!==8'h0b)$fatal(1,"partial drive %h",ord);
    4: if(ord!==8'h2f)$fatal(1,"no store %h",ord);
    6: if(ord!==8'h17)$fatal(1,"bad vector %h",ord);
   endcase
`else
   if(scenario==1 && (ord!==5 || flags[2:0]!==0))$fatal(1,"stage0 witness %h %h",ord,flags);
   if(scenario==3 && ord[3:0]!==5)$fatal(1,"prior inactive read not retained");
   if(scenario==5 && ord[6:4]!==3'b101)$fatal(1,"lost write not recorded");
`endif
   $display("BOOT891 phase=%0d case=%0d lo_drive=%0d hi_drive=%0d lo=%h hi=%h code_bytes=%0d order=%h stage=%h flags=%h write_accepted=%0d",
      ph,scenario,dl,dh,lo,hi,(dl&&dh&&scenario!=6)?39:0,ord,stage,flags,admit);
   if(scenario==0)begin
    // A host write in the middle must not change the pending SPI snapshot.
    fork
     spi(8'h73,8,reply);
     begin wait(dut.screen_status.byte_count==2);first_write(6);end
    join
    if(reply[55:32]!==24'he60100 || reply[23:0]!==24'h000003)$fatal(1,"torn status %h",reply);
    spi(8'h73,4,reply);
    address=24'h007001;write_data=8'ha5;wr=0;#118;wr=1;ticks(10);
    spi(8'h73,8,reply);
    if(reply[55:24]!==32'he606a547 || reply[23:0]!==24'h000103)$fatal(1,"status restart %h",reply);
   end
  end
  $display("PASS BOOT891");$finish;
 end
endmodule
