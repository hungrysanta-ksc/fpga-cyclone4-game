 // Same domain as the collector. Dot 0 of source 1545 anchors the
 // replayed retire offset. Do not pause the PPU while a lease is held.
 integer retire_at, elapsed, off, subcycle, captured, discarded, missed;
 always @(posedge clk) begin
  if (!reset && lease_fault) $fatal(1,"unexpected lease fault");
  if (f>=1545 && f<=1556) begin
   if (capture_begin) begin
    captured++;
    $display("CAP850 %0d %0d",f,generation+1);
   end
   if (effective_release) begin
    if (!export_permitted || geometry_valid || export_error!=2 || !owned)
     $fatal(1,"invalid blank release %0d",f);
    discarded++;
    $display("DROP850 %0d %0d %0d",f,generation,elapsed);
   end
   if (tx_valid) $fatal(1,"blank emitted source bytes");
  end
 end
 task automatic read_visible(input integer source);
  begin
   name=$sformatf("frame%0d.hex",source);$readmemh(name,stimulus);
   name=$sformatf("frame%0d.palette",source);$readmemh(name,palfile);palette=palfile[0];
  end
 endtask
 initial begin
  if (!$value$plusargs("FIRST=%d",first) || !$value$plusargs("LAST=%d",last) || first!=last)
   $fatal(1,"expected retire offset");
  retire_at=first; elapsed=0; captured=0; discarded=0; missed=0;
  repeat(4) @(negedge clk); reset=0; wait(initialized);
  f=1544;read_visible(f);
  cf=$fopen("query1544.txt","w");fd=$fopen("records1544.txt","w");records=0;done=0;
  for(t=0;t<=232*341+1;t++) begin
   @(negedge clk);scanline=t/341;dot=t%341;drive=stimulus[t];ppu_ce=1;
   @(negedge clk);ppu_ce=0;repeat(2)@(negedge clk);
  end
  wait(geometry_valid && owned);@(negedge clk);enable=1;
  wait(done);wait(lease_valid && !owned);@(negedge clk);
  if(captured_generation!=1 || records==0)$fatal(1,"old lease");
  $fclose(fd);$fclose(cf);
  for(f=1545;f<=1557;f++)begin
   if(f==1557)begin
    read_visible(f);records=0;done=0;
    cf=$fopen("query1557.txt","w");fd=$fopen("records1557.txt","w");
   end
   for(t=0;t<262*341;t++)begin
    for(subcycle=0;subcycle<4;subcycle++)begin
     @(negedge clk);
     retire_commit=(elapsed==retire_at);
     if(retire_commit && (!retire_permitted || captured_generation!=1))
      $fatal(1,"retire outside old display lease");
     scanline=t/341;dot=t%341;ppu_ce=(subcycle==0);
     if(f==1557 && t<233*341)drive=stimulus[t];else drive={1'b0,6'd13,100'b0};
     if(f!=1557 && t==7*341+257 && subcycle==1 && !active)missed++;
     elapsed++;
    end
   end
  end
  @(negedge clk);ppu_ce=0;
  wait(done);wait(lease_valid && !owned);
  if(discarded!=captured || missed+captured!=12 || records==0 ||
     generation!=2+captured || captured_generation!=generation || export_error)
   $fatal(1,"bad resume %0d %0d %0d %0d %0d",captured,discarded,missed,generation,records);
  $display("RESUME850 %0d %0d %0d %0d",captured,discarded,missed,generation);
  $fclose(cf);$fclose(fd);
  $display("PASS GEOMETRY230 frames=1");$finish;
 end
 initial begin #110000000;$fatal(1,"capture or retire watchdog");end
endmodule
