 // Included after the board instantiation and SPI helpers from the 891 test.
 reg [63:0] reply;
 integer ph,mode,polls,fd,kind,a,v,mc,opcount,t;
 integer h_ns[2],tag_ns[2],drive_ns[2];
 reg [7:0] code;
 bit driven;
 time origin,started,first_read;
 reg [7:0] witness;
 // SPI1 APB2=84 MHz, BR=4 (/32). Both shipped transfer routines also
 // bracket SS with four 2us waits. Inter-byte firmware stalls are not modeled.
 task automatic wire_spi(input byte op,input integer length,output reg [63:0] head);
  reg [7:0] tx,rx;
  head=0;#2000;ss=0;#2000;
  for(int i=0;i<length;i++)begin
   tx=i==0?op:0;
   for(int pos=7;pos>=0;pos--)begin
    mosi=tx[pos];ticks(16);rx[pos]=miso;sck=1;ticks(16);sck=0;
   end
   if(i<8)head={head[55:0],rx};
   if(op==8'he0 && head[55:48]===8'hf7 && i>=8 &&
      rx!==(i==19?8'hfe:8'h00))$fatal(1,"idle E0 tail/CRC mismatch");
  end
  #2000;ss=1;#2000;
 endtask
 task automatic vector_read(input integer lane);
  address=24'h00fffc+lane;rd=0;wr=1;sel=0;
  h_ns[lane]=-1;tag_ns[lane]=-1;drive_ns[lane]=-1;
  for(int ns=1;ns<=118;ns++)begin
   #1;
   if(dut.sink.host_ready && h_ns[lane]<0)h_ns[lane]=ns;
   if(dut.sink.bus.tag===address && tag_ns[lane]<0)tag_ns[lane]=ns;
   if(dir===1 && oe===0)begin
    if(drive_ns[lane]<0)drive_ns[lane]=ns;
    if(data!==(lane?8'h80:8'h00))$fatal(1,"wrong driven vector");
    if(!dut.sink.host_ready || dut.sink.bus.tag!==address)$fatal(1,"unqualified drive");
   end else if(data!==8'hzz)$fatal(1,"unexpected bus owner");
  end
  if((drive_ns[lane]>=0)!=(mode!=0))$fatal(1,"vector ownership mode=%d lane=%d",mode,lane);
  sel=1;rd=1;#25;
 endtask
 initial begin
  force dut.host_clk=clk;force dut.host_locked=1;force dut.power_reset=reset_request;
  // Model a verified START/STOP and valid board clocks. Keep the real NES
  // memory scrub, both reset-release chains, bridge admission, ROM and top OE.
  force dut.core.run_enable=session;force dut.core.boot_reset=0;
  for(ph=0;ph<4;ph++)for(mode=0;mode<3;mode++)begin
   reset_request=1;session=0;wr=1;rd=1;sel=1;ss=1;address=0;ticks(30);
   reset_request=0;ticks(30);
   // /WR may be low during RESET. Mode 2 exercises READY before release.
   wr=(mode==2);session=1;started=$time;
   if(mode==2)begin wait(dut.sink.host_ready===1);ticks(3);end
   wire_spi(8'h65,8,reply); // status transaction after verified START
   wire_spi(8'he0,20,reply);
   if((reply[55:48]===8'hf7)!=(mode==2))$fatal(1,"pre-release E0 %h",reply);
   polls=0;
   if(mode==1)begin
    do begin
     wire_spi(8'h73,8,reply);polls++;
     $display("SNAP892 phase=%0d reply=%h",ph,reply[55:0]);
     if(reply[55:48]!==8'he6 || reply[7:0]!==3 || polls>64)$fatal(1,"SPI73");
    end while(reply[30]!==1); // flags byte bit 6 = synchronized RUN && !core_reset
    if(dut.sink.host_ready!==0)$fatal(1,"admitted a held write");
   end
   @(negedge clk);#(1+3*ph);
   first_read=$time;
   if(dut.core.memory_ready!==(mode!=0))$fatal(1,"cold initialization boundary");
   vector_read(0);vector_read(1);
   if(mode==0)begin
    // Causal control: give the tag the requested address without changing admission.
    address=24'h00fffc;rd=0;sel=0;force dut.sink.bus.tag=24'h00fffc;#118;
    if(dut.sink.host_ready || oe!==1 || data!==8'hzz)$fatal(1,"tag alone opened the bridge");
    release dut.sink.bus.tag;rd=1;sel=1;#25;
   end
   opcount=0;
   if(mode!=0)begin
    origin=$time;
    fd=$fopen("cpu.txt","r");
    if(!fd)$fatal(1,"missing CPU replay");
    while($fscanf(fd,"%c %h %h %d\n",kind,a,v,mc)==4)begin
     if($time<origin+(mc-186)*46.566) #(origin+(mc-186)*46.566-$time);
     if(kind=="w")begin
      if(a!='h7000 || v!=1 || mc!=640)$fatal(1,"wrong first store");
      first_write(v);
     end else begin
      fetch(a,code,driven);
      if(!driven || code!==v[7:0])$fatal(1,"CPU replay %h",a);
      opcount++;
     end
    end
    $fclose(fd);
    if(opcount<16 || dut.screen_status.stage!==1)$fatal(1,"first stage missing");
   end
   wait(dut.sink.host_ready===1);wire_spi(8'he0,20,reply);
   if(reply[55:48]!==8'hf7)$fatal(1,"post-release E0");
   wire_spi(8'h73,8,reply);witness=dut.screen_status.boot_order;
   if(mode==0 && (reply[47:32]!==16'h0003 || (reply[31:24]&7)!=0))$fatal(1,"physical failure signature %h",reply);
   if(mode!=0 && (reply[47:40]!==1 || witness!==8'h6f))$fatal(1,"incomplete success %h",reply);
   // Test a late tag while fully admitted. A changing address must revoke drive.
   address=24'h00fffc;sel=0;rd=0;#118;
   if(data!==8'h00 || oe!==0)$fatal(1,"stop setup");
   address=24'h00fffd;#1;
   if(!dut.sink.host_ready || oe!==1 || data!==8'hzz)$fatal(1,"stale tag drove bus");
   #117;if(data!==8'h80)$fatal(1,"late tag did not recover");
   session=0;#1;
   if(oe!==1 || dir!==0 || data!==8'hzz)$fatal(1,"STOP during vector read");
   ticks(8);if(dut.sink.host_ready!==0)$fatal(1,"STOP retained host admission");
   $display("RESET892 mode=%0d phase=%0d release_ns=%0d polls=%0d lo_host=%0d lo_tag=%0d lo_drive=%0d hi_host=%0d hi_tag=%0d hi_drive=%0d witness=%h stage=%h code_reads=%0d",
    mode,ph,first_read-started,polls,h_ns[0],tag_ns[0],drive_ns[0],h_ns[1],tag_ns[1],drive_ns[1],witness,reply[47:40],opcount);
  end
  $display("PASS RESET892");$finish;
 end
endmodule
