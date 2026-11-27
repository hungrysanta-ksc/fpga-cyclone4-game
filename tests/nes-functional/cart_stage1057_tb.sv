`timescale 1ns/1ps
module cart_stage1057_tb;
 reg clk=0;
 always #5 clk=!clk;
 task tick;begin @(posedge clk);#1;end endtask
 reg rst=1, demand=0, sample=0, resp=0, hint=0;
 reg [21:0] addr=0, tag=0, guess=0;
 reg [7:0] plane0=0,plane1=0;
 wire req,valid,fault;wire [3:0] cause;wire [21:0] request_addr;wire [7:0] data;
 nes_rom_early rom(.clk(clk),.reset(rst),.cpu_address_valid(1'b0),.cpumem_read(1'b0),
   .cpumem_addr(25'h380000),.cpu_sample(1'b0),.ppu_prefetch_valid(hint),
   .ppu_prefetch_address(guess),.ppu_address_valid(demand),.ppumem_addr(addr),.ppumem_read(demand),
   .ppu_sample(sample),.ppu_data(data),.ppu_valid(valid),.rom_ready(1'b1),.rom_request(req),
   .rom_address(request_addr),.rom_response(resp),.rom_error(1'b0),.rom_response_address(tag),
   .rom_data(plane0),.chr_plane1(plane1),.fault(fault),.error_code(cause));
 reg start=0,rendering=0,finish=0,changed=0,discard=0,retire=0,read_req=0;
 reg [12:0] wr_addr=0;reg [7:0] wr_data=0;
 reg [17:0] read_addr=0; reg [15:0] owner=4,reader=4;
 wire ready,can_start,conflict,reply,err,oe,we,drive,fine;
 wire [7:0] clean,rd,out;wire [12:0] scan;wire [18:0] ram;
 reg [7:0] live[0:8191],mirror[0:8191];reg [7:0] scan_q;
 always @(posedge clk) begin
   scan_q<=live[scan];
   if(changed)live[wr_addr]<=wr_data;
   if(!we && drive)mirror[ram[12:0]]<=out;
 end
 nes_chr_snapshot snap(.clk(clk),.reset(rst),.rendering(rendering),.capture_end(finish),
  .start(start),.collecting(1'b1),.changed(changed),.changed_group(wr_addr[12:7]),
  .retire(retire),.discard(discard),.start_gen(owner),.retire_gen(owner),.read_gen(reader),
  .can_start(can_start),.conflict(conflict),.fine_receipt(fine),.clean_pages(clean),
  .scan_addr(scan),.scan_data(scan_q),.read_req(read_req),.read_addr(read_addr),.cancel(1'b0),
  .ready(ready),.response(reply),.error(err),.data(rd),.ram_addr(ram),.oe_n(oe),.we_n(we),
  .ram_q(mirror[ram[12:0]]),.drive_data(drive),.write_data(out));
 integer i,fd,n,offset,expected,lo_value,hi_value,demands,grants;
 task check_tile(input [21:0] a,input [7:0] lo,hi);
 begin
   addr=a;demand=1;#1;
   if(!req || request_addr!=(a & 22'h3ffff7))$fatal(1,"row request %h",a);
   tag=request_addr;tick();resp=1;plane0=lo;plane1=hi;sample=1;#1;
   if(!valid || data!==(a[3]?hi:lo))$fatal(1,"reply");
   tick();resp=0;addr=a^8;#1;
   if(!valid || req || data!==(a[3]?lo:hi))$fatal(1,"companion read");
   tick();sample=0;demand=0;
 end endtask
 task capture;begin start=1;tick();start=0;end endtask
 task seal_frame;begin finish=1;tick();finish=0;end endtask
 task mutate(input [12:0] a,input [7:0] v);
 begin wr_addr=a;wr_data=v;changed=1;tick();changed=0;end endtask
 initial begin
   for(i=0;i<8192;i=i+1)live[i]=(i^(i>>8));
   tick();rst=0;tick();
   check_tile(22'h21234a,8'h51,8'hd7);
   check_tile(22'h202342,8'h53,8'hd9);
   addr=22'h212342;sample=1;#1;if(!valid||data!=8'h51)$fatal(1,"previous row");
   sample=0;guess=22'h20234a;hint=1;#1;if(req)$fatal(1,"redundant hint");
   hint=0;addr=22'h212343;sample=1;tick();
   if(!fault||cause!=2)$fatal(1,"unserved deadline");
   rst=1;tick();rst=0;sample=0;addr=0;#1;if(valid||fault)$fatal(1,"STOP");
   // Original Waiwai stage, in actual fetch order. Supply only the requested
   // physical ROM word and compare each selected lane to Mesen's PPU byte.
   fd=$fopen("rows.txt","r");if(!fd)$fatal(1,"missing reference");
   demands=0;grants=0;
   while(!$feof(fd))begin
     n=$fscanf(fd,"%h %h %h %h",offset,expected,lo_value,hi_value);
     if(n==4)begin
       addr=22'h200000+offset;demand=1;#1;
       if(req)begin
         tag=request_addr;
         if(tag!==(addr & 22'h3ffff7))$fatal(1,"wrong ROM bank or row");
         tick();resp=1;plane0=lo_value;plane1=hi_value;grants=grants+1;
       end
       sample=1;#1;
       if(!valid || data!==expected[7:0])$fatal(1,"stage CHR read %h expected %h got %h",addr,expected,data);
       tick();sample=0;resp=0;demands=demands+1;
     end else if(n!= -1)$fatal(1,"malformed reference");
   end
   $fclose(fd);demand=0;
   if(demands<10000 || grants==0 || grants>=demands)$fatal(1,"reference coverage");
   $display("PASS_WAIWAI_STAGE PPU reads=%0d PSRAM grants=%0d",demands,grants);
   // Rendering starts on line 15. Writes straddle capture start on line 7.
   capture();mutate(13'h0084,8'hc8);mutate(13'h0103,8'h2d);
   if(conflict||ready||fine||clean)$fatal(1,"blank prefix");
   rendering=1;repeat(50000)tick();if(ready)$fatal(1,"unsealed access");
   seal_frame();if(conflict||!ready)$fatal(1,"clean snapshot missed");
   for(i=0;i<8192;i=i+1)if(mirror[i]!==live[i])$fatal(1,"bad snapshot byte %d",i);
   mutate(13'h0084,8'hff);read_addr=18'h84;read_req=1;tick();read_req=0;
   repeat(3)tick();if(!reply||err||rd!=8'hc8)$fatal(1,"lease changed");
   tick();reader=5;read_req=1;tick();read_req=0;if(!reply||!err)$fatal(1,"generation");
   retire=1;tick();retire=0;owner=5;rendering=0;capture();rendering=1;tick();
   mutate(13'h0084,8'h01);if(!conflict)$fatal(1,"visible mutation accepted");
   discard=1;tick();discard=0;rendering=0;capture();mutate(13'h0104,8'h81);
   seal_frame();if(!conflict||ready)$fatal(1,"incomplete snapshot accepted");
   rst=1;tick();if(ready||reply||!we||!oe)$fatal(1,"STOP drove memory");
   // Load observed stage bytes, deferring the animated prefix into the blank
   // part of capture, then read them back in the game's actual PPU order.
   fd=$fopen("pattern-7.txt","r");if(!fd)$fatal(1,"missing Battletoads reference");
   while(!$feof(fd))begin
     n=$fscanf(fd,"%h %h",offset,expected);
     if(n==2 && offset>=384)live[offset]=expected;
   end
   $rewind(fd);rst=0;rendering=0;reader=owner;capture();
   while(!$feof(fd))begin
     n=$fscanf(fd,"%h %h",offset,expected);
     if(n==2 && offset<384 && live[offset]!==expected[7:0])mutate(offset,expected);
   end
   rendering=1;repeat(50000)tick();seal_frame();
   if(!ready||conflict)$fatal(1,"stage mirror rejected");
   demands=0;$rewind(fd);
   while(!$feof(fd))begin
     n=$fscanf(fd,"%h %h",offset,expected);
     if(n==2)begin
       read_addr=offset;read_req=1;tick();read_req=0;repeat(3)tick();
       if(!reply||err||rd!==expected[7:0])$fatal(1,"stage CHR RAM %h",offset);
       tick();demands=demands+1;
     end
   end
   $fclose(fd);if(demands<10000)$fatal(1,"Battletoads stage coverage");
   $display("PASS_BATTLE_STAGE PPU reads=%0d",demands);
   $display("PASS1057 both CHR planes, full physical tags, unserved deadline, 8192 snapshot bytes, blank prefix, visible conflict, immutable lease, STOP");
   $finish;
 end
endmodule
