// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module source_tile192_tb;
 parameter integer SCENE=0,MODE=0,USE_CACHE=1;
 parameter real PHASE=0.0;
 reg clk=0,mem_clk=0,reset=1,stop=0,owned=1,geometry=1,isrom=1,writing=0;
 always #23.280423 clk=!clk;
 initial begin #(PHASE);forever #2.9761905 mem_clk=!mem_clk;end
 reg [31:0] epoch=7,capture_epoch=7;reg pv=0;wire pr;
 reg [1:0] kind=0;reg [15:0] gen=100+SCENE;reg [9:0] slot=1;reg [12:0] tag=0;
 reg [47:0] rows=0;reg [7:0] mask=255,am=0;reg [103:0] ats=0;
 wire req,mready,mresponse,merror,cr,cv,ce;
 wire [21:0] address,ra,cra;wire [7:0] rd,cd;
 wire ov;wire [7:0] od;wire [4:0] oi;wire [5:0] length;wire [1:0] ok;
 wire [9:0] os;wire [15:0] og;wire busy,fault,done,drained;
 integer cycle=0,framecycle=316448,checked=0,reads=0,tiles=0,stall=0,core_reads=0;
 integer first_read=-1,last_read=0,windows=0,previous_window=-1,denied_checks=0;
 reg schedule=1,check_output=1,check_new=0;
 wire grant_window=framecycle>=330088&&framecycle<354640;
 wire qualified=schedule?(grant_window&&cycle%12==3):1'b1;
 wire core_req=schedule&&qualified&&cycle%120==3&&cr;
 wire out_ready=cycle%5!=0;
 nes_source_tile192 #(.USE_CACHE(USE_CACHE)) dut(.clk(clk),.reset(reset),.stop(stop),.frame_owned(owned),.geometry_valid(geometry),
  .frame_generation(16'(100+SCENE)),.source_ready(1'b1),.source_is_rom(isrom),.source_writing(writing),
  .captured_epoch(capture_epoch),.live_epoch(epoch),.plan_valid(pv),.plan_ready(pr),.plan_kind(kind),
  .plan_generation(gen),.plan_slot(slot),.plan_tag(tag),.plan_rows(rows),.plan_mask(mask),.plan_alt_mask(am),.plan_alt_tags(ats),
  .qualified_slot(qualified),.core_safe(1'b1),.core_request(core_req),.core_address(22'h001234),
  .core_ready(cr),.core_response(cv),.core_error(ce),.core_response_address(cra),.core_data(cd),
  .mem_ready(mready),.mem_response(mresponse),.mem_error(merror),.mem_response_address(ra),.mem_data(rd),
  .mem_request(req),.mem_address(address),.out_valid(ov),.out_ready(out_ready),.out_data(od),.out_index(oi),
  .out_length(length),.out_kind(ok),.out_slot(os),.out_generation(og),.busy(busy),.done(done),.fault(fault),.drained(drained));
 wire [21:0] psram_address;wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;wire [15:0] psram_data;
 nes_rom_physical #(.READ_CYCLES(16)) reader(.clk(clk),.mem_clk(mem_clk),.reset(reset),
  .check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),.check_ready(),.check_response(),.check_response_address(),.check_data(),
  .rom_request(req),.rom_address(address),.rom_ready(mready),.rom_response(mresponse),.rom_error(merror),
  .rom_response_address(ra),.rom_data(rd),.psram_address(psram_address),.psram_1ce(psram_1ce),.psram_2ce(psram_2ce),
  .psram_oe(psram_oe),.psram_we(psram_we),.psram_bhe(psram_bhe),.psram_ble(psram_ble),.psram_data(psram_data));
 reg [7:0] memory[0:159],expected[0:32767];
 function automatic [7:0] value(input [23:0] a);
  if(a>=24'h200000&&a<24'h2000a0)value=memory[a-24'h200000];
  else value=a[7:0]^a[15:8]^a[23:16];
 endfunction
 wire selected=(!psram_1ce ^ !psram_2ce)&&!psram_oe&&psram_we;
 wire [23:0] base={psram_address,psram_1ce,1'b0};
 assign #70 psram_data=selected?{psram_bhe?8'hzz:value(base),psram_ble?8'hzz:value(base+1)}:16'hzzzz;
 always @(posedge clk)begin
  cycle<=cycle+1;framecycle<=framecycle==357367?0:framecycle+1;
  if(req&&mready)begin
   if(core_req)begin
    if(address!=22'h1234)$fatal(1,"core priority lost");
   end else begin
    if(schedule&&!qualified)$fatal(1,"unqualified source read");
    if(address[21:17]!=5'h10)$fatal(1,"wrong physical source map");
    reads<=reads+1;if(first_read<0)first_read<=cycle;last_read<=cycle;
    if((cycle+316448)/357368!=previous_window)begin windows<=windows+1;previous_window<=(cycle+316448)/357368;end
   end
  end
  if(cv)begin
   if(ce||cra!=22'h1234||cd!==value(24'h1234))$fatal(1,"core reply corrupted");
   core_reads<=core_reads+1;
  end
  if(ov&&!out_ready)stall<=stall+1;
  if(ov&&out_ready&&check_new&&od!==memory[{tag,oi[0],3'(rows>>(oi*3))}])$fatal(1,"stale cached byte");
  if(ov&&out_ready&&check_output)begin
   if(od!==expected[MODE==1?16+(checked%16):checked]||ok!=kind||os!=slot||og!=gen||length!=(kind==1?32:16))
    $fatal(1,"output mismatch scene=%d byte=%d got=%x",SCENE,checked,od);
   checked<=checked+1;
  end
 end
 task tick;begin @(posedge clk);#1;end endtask
 task submit;
  begin while(!pr&&!fault)tick();if(fault)$fatal(1,"not ready");@(negedge clk);pv=1;tick();@(negedge clk);pv=0;end
 endtask
 task complete;
  begin while(!done&&!fault)tick();if(fault)$fatal(1,"unexpected source fault");tiles=tiles+1;end
 endtask
 task recover;
  begin @(negedge clk);stop=1;pv=0;owned=0;tick();@(negedge clk);stop=0;
   while(!drained)tick();epoch=7;isrom=1;writing=0;geometry=1;@(negedge clk);owned=1;tick();
   if(fault||busy)$fatal(1,"failed recovery");end
 endtask
 integer f,n,j,before_reads;reg [1023:0] filename;
 initial begin
  $sformat(filename,"scene%0d.mem",SCENE);$readmemh(filename,memory,0,159);
  $sformat(filename,"scene%0d.expected",SCENE);$readmemh(filename,expected);
  $sformat(filename,"scene%0d.rtl",SCENE);f=$fopen(filename,"r");if(!f)$fatal(1,"plans missing");
  repeat(5)tick();reset=0;wait(drained);tick();
  if(MODE==0)begin
   while(!$feof(f))begin
    @(negedge clk);n=$fscanf(f,"%h %h %h %h %h %h %h %h\n",kind,gen,slot,tag,mask,rows,am,ats);
    if(n==8)begin submit();complete();end else if(n!=-1&&n!=0)$fatal(1,"fixture");
   end
  end else begin
   // First ordinary BG plan from the same actual186 reference (after zero).
   n=$fscanf(f,"%h %h %h %h %h %h %h %h\n",kind,gen,slot,tag,mask,rows,am,ats);
   n=$fscanf(f,"%h %h %h %h %h %h %h %h\n",kind,gen,slot,tag,mask,rows,am,ats);
   if(n!=8||kind!=0)$fatal(1,"BG plan absent");
   if(MODE==1)begin for(j=0;j<512;j=j+1)begin submit();complete();end end
   else begin
    schedule=0;check_output=0;
    // Unsupported mutable source, changed epoch and write window deny reads.
    for(j=0;j<3;j=j+1)begin
     @(negedge clk);if(j==0)isrom=0;if(j==1)epoch=8;if(j==2)writing=1;pv=1;
     tick();if(pr||req||ov||!fault)$fatal(1,"unsafe source admitted");denied_checks++;
     recover();
    end
    // Revocation and STOP with a real physical read in flight must drain it.
    for(j=0;j<2;j=j+1)begin
     submit();wait(req&&mready);tick();@(negedge clk);
     if(j==0)epoch=8;else stop=1;
     #1;if(ov||pr||drained)$fatal(1,"premature release");
     tick();if(j==0&&!fault)$fatal(1,"epoch revocation missed");
     while(!drained)begin tick();if(ov||cv)$fatal(1,"stale reply exposed");end
     denied_checks++;recover();
    end
    // New command after actual flush completes; no stale response substitution.
    check_output=0;submit();complete();denied_checks++;
    // Reuse a warm tile, then change the ROM content epoch through a write
    // window with no active frame. A fresh capture may not see cached bytes.
    if(USE_CACHE)begin
     before_reads=reads;submit();complete();
     if(reads!=before_reads)$fatal(1,"warm tile was reread");denied_checks++;
     @(negedge clk);owned=0;writing=1;tick();
     for(j=0;j<160;j=j+1)memory[j]=memory[j]^8'hff;
     @(negedge clk);epoch=8;tick();@(negedge clk);capture_epoch=8;writing=0;owned=1;
     check_new=1;tick();before_reads=reads;submit();complete();
     if(reads-before_reads!=16)$fatal(1,"epoch did not invalidate all lanes");denied_checks++;
     // Even simultaneous new captured/live epochs must invalidate the cache;
     // equality of those inputs does not imply equality with cached content.
     @(negedge clk);owned=0;tick();@(negedge clk);epoch=9;capture_epoch=9;
     for(j=0;j<160;j=j+1)memory[j]=memory[j]^8'h3c;
     tick();@(negedge clk);owned=1;tick();before_reads=reads;submit();complete();
     if(reads-before_reads!=16)$fatal(1,"equal new epochs retained old cache");denied_checks++;
    end
    $display("PASS SOURCE192FAULT cases=%0d",denied_checks);$finish;
   end
  end
  $fclose(f);
  if(!checked||!core_reads||!stall)$fatal(1,"missing coverage");
  $display("PASS SOURCE192 scene=%0d mode=%0d tiles=%0d bytes=%0d reads=%0d core=%0d windows=%0d first=%0d last=%0d cycles=%0d",SCENE,MODE,tiles,checked,reads,core_reads,windows,first_read,last_read,cycle);$finish;
 end
 initial begin #500000000;$fatal(1,"timeout");end
endmodule
