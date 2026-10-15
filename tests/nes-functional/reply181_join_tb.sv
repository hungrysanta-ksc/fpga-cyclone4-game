// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Real service/arbiter/FIFO fill/reader; modeled CPU/PPU schedules and 70ns pins.
// No whole-game, metastability or placed timing claim.
module reply181_join_case #(parameter realtime PHASE=0)(output reg finished=0);
 reg clk=0,mem_clk=0,reset=1;
 always #22.727 clk=~clk;
 initial begin #(PHASE);forever #2.9761905 mem_clk=~mem_clk;end
 reg cpu_address_valid=0,ppu_address_valid=0,cpumem_read=0,cpu_sample=0;
 reg ppumem_read=0,ppu_sample=0,ppu_prefetch_valid=0;
 reg [24:0] cpumem_addr=0;
 reg [21:0] ppumem_addr=22'h3a0000,ppu_prefetch_address=0;
 wire [7:0] cpu_data,ppu_data,cd,md,fd;
 wire cpu_valid,ppu_valid,safe,cr,cq,cp,ce,mr,mq,mp,me;
 wire [21:0] ca,cpa,ma,mpa;
 wire fault_trigger,service_fault,arb_fault;
 wire [63:0] fault_context;wire [3:0] error_code;wire [11:0] history_flags157;
 nes_rom_early service(.clk(clk),.reset(reset),.native_core_safe(safe),
 .cpu_address_valid(cpu_address_valid),.ppu_address_valid(ppu_address_valid),
 .cpumem_addr(cpumem_addr),.cpumem_read(cpumem_read),.cpu_sample(cpu_sample),
 .ppumem_addr(ppumem_addr),.ppumem_read(ppumem_read),.ppu_sample(ppu_sample),
 .ppu_prefetch_valid(ppu_prefetch_valid),.ppu_prefetch_address(ppu_prefetch_address),
 .cpu_data(cpu_data),.ppu_data(ppu_data),.cpu_valid(cpu_valid),.ppu_valid(ppu_valid),
 .rom_ready(cr),.rom_request(cq),.rom_address(ca),.rom_response(cp),.rom_error(ce),
 .rom_response_address(cpa),.rom_data(cd),.history_flags157(history_flags157),
 .fault_trigger(fault_trigger),.fault_context(fault_context),.fault(service_fault),.error_code(error_code));
 reg start=0,clear=0,owned=1,slot=0,consume=1;
 reg [15:0] generation=1;
 wire fq,fr,fi,fp,fe,fa,req,bv,busy,done,quarantine,success;
 wire [2:0] qk;wire [12:0] qi,bt;wire [15:0] qg,fg,rg,bg;
 wire [21:0] faddr,fpa;wire [7:0] bd;wire [3:0] bl,ferror;
 wire [1:0] bk;wire [9:0] tiles;wire [13:0] bytes;wire [31:0] cycles;
 reg qr=0;reg [63:0] qd=0;
 always @(posedge clk)begin qr<=fq;qd<=(qi==0||qi==1||qi==8191)?64'd1:0;end
 nes_native_fill165 #(.WAIT_CYCLES(1024),.COOPERATIVE_WAIT(1)) fill(
 .clk(clk),.reset(reset),.start(start),.clear(clear),.frame_owned(owned),.geometry_valid(1'b1),.frame_generation(generation),
 .query(fq),.query_kind(qk),.query_index(qi),.query_generation(qg),.response(qr),.hit(1'b1),.data(qd),
 .mem_idle(fi),.mem_ready(fr),.mem_response(fp),.mem_error(fe),.mem_response_address(fpa),.mem_response_generation(rg),.mem_data(fd),
 .mem_request(req),.mem_abort(fa),.mem_address(faddr),.mem_generation(fg),
 .byte_valid(bv),.byte_ready(consume),.byte_data(bd),.byte_tile(bt),.byte_lane(bl),.byte_kind(bk),.byte_generation(bg),
 .busy(busy),.done(done),.quarantine(quarantine),.success(success),.error(ferror),.tile_count(tiles),.byte_count(bytes),.cycles(cycles));
 nes_native_arbiter165 arb(.clk(clk),.reset(reset),.slot(slot),.core_safe(safe),
 .core_request(cq),.core_address(ca),.core_ready(cr),.core_response(cp),.core_error(ce),.core_response_address(cpa),.core_data(cd),
 .fill_request(req),.fill_abort(fa),.fill_address(faddr),.fill_generation(fg),.fill_ready(fr),.fill_idle(fi),
 .fill_response(fp),.fill_error(fe),.fill_response_address(fpa),.fill_response_generation(rg),.fill_data(fd),
 .mem_ready(mr),.mem_response(mp),.mem_error(me),.mem_response_address(mpa),.mem_data(md),.mem_request(mq),.mem_address(ma),.fault(arb_fault));
 wire [21:0] psram_address;wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;wire [15:0] psram_data;
 nes_rom_physical #(.READ_CYCLES(16)) reader(.clk(clk),.mem_clk(mem_clk),.reset(reset),
 .check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),.check_ready(),.check_response(),.check_response_address(),.check_data(),
 .rom_request(mq),.rom_address(ma),.rom_ready(mr),.rom_response(mp),.rom_error(me),.rom_response_address(mpa),.rom_data(md),
 .psram_address(psram_address),.psram_1ce(psram_1ce),.psram_2ce(psram_2ce),.psram_oe(psram_oe),.psram_we(psram_we),.psram_bhe(psram_bhe),.psram_ble(psram_ble),.psram_data(psram_data));
 rom_physical_model #(.ACCESS_NS(70)) memory(.*);
 function automatic [7:0] value(input [23:0] address);
  value=address[7:0]^address[15:8]^{address[19:16],address[23:20]}^8'hb7;
 endfunction
 integer ticks=0,replies=0,core_replies=0,fill_replies=0,pops=0,sameedge=0,max_age=0,cancels=0,resets=0;
 integer samples=0,priority_hits=0,discarded=0;
 always @(posedge clk)begin
  ticks=ticks+1;
  if(!reset)begin
   if(service_fault||fault_trigger||arb_fault)$fatal(1,"joined fault %0d",error_code);
   if(mp)begin
    if(md!==value({2'b0,mpa}))$fatal(1,"qualified byte %h got%h expected%h",mpa,md,value({2'b0,mpa}));
    replies++;if(mq)sameedge++;
    if(arb.owner && (arb.discard||fa))begin
     if(fp||cp)$fatal(1,"discard leaked");discarded++;
    end
   end
   if(cp)core_replies++;
   if(fp)begin fill_replies++;if(arb.age>max_age)max_age=arb.age;if(arb.age>6)$fatal(1,"seven-edge bound");end
   if(cq&&req&&slot)begin if(!mq||ma!==ca||fr)$fatal(1,"priority_hits lost");priority_hits++;end
   if(cpu_sample)begin if(!cpu_valid||cpu_data!==value({2'b0,cpumem_addr[21:0]}))$fatal(1,"CPU sample");samples++;end
   if(ppu_sample)begin if(!ppu_valid||ppu_data!==value({2'b0,ppumem_addr}))$fatal(1,"PPU sample");samples++;end
   if(bv&&consume)begin
    if(bd!==value({7'h10,bt,bl})||bg!=generation||bk!=1)$fatal(1,"FIFO data/tag");pops++;
   end
  end
 end
 task tick;begin @(negedge clk);end endtask
 task fresh;
  begin reset=1;cpu_address_valid=0;ppu_address_valid=0;ppu_prefetch_valid=0;cpu_sample=0;ppu_sample=0;
   cpumem_read=0;ppumem_read=0;start=0;clear=0;slot=0;consume=1;owned=1;
   repeat(4)tick();reset=0;repeat(5)tick();if(!mr||quarantine)$fatal(1,"reset release");
  end
 endtask
 task cpu(input [21:0] address);
  begin cpumem_addr=address;cpu_address_valid=1;
   do tick();while(!cpu_valid);
   cpu_sample=1;tick();cpu_sample=0;
  end
 endtask
 task ppu(input [21:0] address);
  begin ppumem_addr=address;ppu_address_valid=1;
   do tick();while(!ppu_valid);
   ppu_sample=1;tick();ppu_sample=0;
  end
 endtask
 task launch_fill;
  begin start=1;tick();start=0;end
 endtask
 integer i,before_pops;
 initial begin
  fresh();
  for(i=0;i<24;i++)begin cpu(22'(i*1031));ppu(22'h200000+22'(i*521));end
  // A different speculation is accepted on the very edge consuming a reply.
  ppu_address_valid=0;ppu_prefetch_valid=1;ppu_prefetch_address=22'h210321;
  do tick();while(!cp);
  ppu_prefetch_address=22'h211239;#1;if(!cq)$fatal(1,"next request on response edge");
  tick();ppu_prefetch_valid=0;do tick();while(service.busy);
  ppu(22'h210321);ppu(22'h211239);ppu_address_valid=0;
  // Hold a cached CPU address, the production prerequisite for fill slots.
  cpu(22'h002b30);slot=0;launch_fill();wait(req);tick();
  cpumem_addr=22'h003b31;slot=1;#1;if(!cq||fr)$fatal(1,"core must outrank fill");
  do tick();while(!cpu_valid);cpu_sample=1;tick();cpu_sample=0;
  consume=0;repeat(30)tick();consume=1;before_pops=pops;
  wait(done);tick();if(!success||bytes!=48||tiles!=3||pops-before_pops!=48)$fatal(1,"fill completion");
  // Abort each pending-read age, drain old reply, then reuse without reader reset.
  for(i=0;i<5;i++)begin
   clear=1;tick();clear=0;generation++;wait(!quarantine&&fi);tick();launch_fill();
   wait(arb.owner);tick();repeat(i)tick();clear=1;tick();clear=0;cancels++;
   wait(fi&&!quarantine);tick();if(done||busy||fp)$fatal(1,"abort did not drain i=%0d done=%b busy=%b response=%b",i,done,busy,fp);
  end
  // Common reset during both core and fill reads; no stale response on recovery.
  for(i=0;i<5;i++)begin
   slot=0;cpumem_addr=22'h010000+22'(i*1033);tick();repeat(i)tick();fresh();resets++;
   cpu(22'h013012+22'(i*9));slot=1;launch_fill();wait(arb.owner);repeat(i)tick();fresh();resets++;
  end
  if(sameedge==0||priority_hits==0||discarded==0||fill_replies<48||samples<50)$fatal(1,"coverage");
  $display("PASS REPLYJOIN181 phase=%0.3f ticks=%0d replies=%0d core=%0d fill=%0d samples=%0d sameedge=%0d priority_hits=%0d discard=%0d maxage=%0d cancels=%0d resets=%0d",PHASE,ticks,replies,core_replies,fill_replies,samples,sameedge,priority_hits,discarded,max_age,cancels,resets);
  finished=1;
 end
endmodule
module reply181_join_tb;
 wire [15:0] done;
 generate for(genvar k=0;k<16;k++)begin:phases
  reply181_join_case #(.PHASE(k*0.375)) c(done[k]);
 end endgenerate
 initial begin wait(&done);$display("PASS REPLYJOIN181 all16");$finish;end
 initial begin #5000000;$fatal(1,"join watchdog");end
endmodule
