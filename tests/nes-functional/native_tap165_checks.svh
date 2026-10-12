// SPDX-License-Identifier: MIT
// Included in the actual CPU/PPU/MMC3 game harness, not a driven PPU schedule.
 reg native_freeze=0,native_release_cache=0,native_query=0;
 reg [8:0] native_query_slot=0;
 reg [17:0] native_query_tag=0;
 reg [4:0] native_query_offset=0;
 reg native_query_obj4=0;
 wire native_initialized,native_owned,native_response,native_hit;
 wire [7:0] native_data;wire [15:0] native_valid_bytes;
 reg [17:0] expected_tag[0:511];
 reg [15:0] expected_mask[0:511];
 integer captured=0,bank_changes=0,queries=0,complete_tiles=0,partial_tiles=0,empty_tiles=0;
 integer tile,offset,lane,slot,control=0,ignored_control;
 reg [31:0] pixel_hash=32'h811c9dc5,bus_hash=32'h811c9dc5;
 reg [21:0] delayed_physical;
 initial begin
  ignored_control=$value$plusargs("CONTROL=%d",control);
  for(integer t=0;t<512;t++)begin expected_tag[t]=0;expected_mask[t]=0;end
 end
 // This is independent of the adapter's internal accept signal.
 always @(posedge clk)begin
  delayed_physical<=ppumem_addr;
  if(!reset)begin
   if(rom_cpu_sample && cpumem_addr<25'h40000 && rom_cpu_valid)
    bus_hash=(bus_hash ^ {6'd0,cpumem_addr[17:0],cpumem_din})*32'h01000193;
   if(tap_ce && ppumem_read && rom_ppu_valid)
    bus_hash=(bus_hash ^ {2'd0,ppumem_addr,ppumem_din})*32'h01000193;
   if(frame>0 && tap_ce && scanline<240 && cycle>=2 && cycle<=257)
    pixel_hash=(pixel_hash ^ {23'd0,emphasis,color})*32'h01000193;
   if(native_initialized && !native_owned && !native_freeze && !native_capture.cache.draining &&
      tap_ce && ppumem_read && !dut.core.chr_addr[13] &&
      rom_ppu_valid && !rom_fault && ppumem_addr>=22'h200000 && ppumem_addr<22'h220000)begin
    if(native_chr_logical!==dut.core.ppu.vram_addr || ppumem_addr!==dut.core.chr_linaddr ||
       ppumem_din!==chr[ppumem_addr[16:0]] || native_chr_logical[3:0]!==ppumem_addr[3:0])
      $fatal(1,"same-edge tap disagrees with consumed PPU byte");
    if(!control)begin
     slot=native_chr_logical[12:4];
     if(expected_tag[slot]!=ppumem_addr[21:4])begin
      if(expected_mask[slot]!=0)bank_changes++;
      expected_tag[slot]=ppumem_addr[21:4];expected_mask[slot]=0;
     end
     expected_mask[slot][native_chr_logical[3:0]]=1;captured++;
    end
   end
  end
 end
 task verify_native;
  begin
   // Stop only the cache; CPU/PPU continue running during all queries.
   native_freeze=1;wait(native_owned);@(negedge clk);native_freeze=0;
   for(tile=0;tile<512;tile++)begin
    if(expected_mask[tile]==16'hffff)complete_tiles++;
    else if(expected_mask[tile]!=0)partial_tiles++;
    else empty_tiles++;
    for(offset=0;offset<48;offset++)begin
     @(negedge clk);native_query_slot=tile;native_query_tag=expected_tag[tile];
     native_query_obj4=offset>=16;native_query_offset=offset>=16?offset-16:offset;
     native_query=1;@(negedge clk);native_query=0;@(negedge clk);
     lane=(native_query_offset%2)*8+native_query_offset/2;
     if(native_response!==1 || native_valid_bytes!==expected_mask[tile] ||
        native_hit!==(expected_mask[tile]==16'hffff))$fatal(1,"metadata differs tile=%0d got=%h want=%h",tile,native_valid_bytes,expected_mask[tile]);
     if(native_data!==((expected_mask[tile]==16'hffff && native_query_offset<16)?
         chr[((expected_tag[tile]-18'h20000)*16)+lane]:8'd0))$fatal(1,"CHR byte/plane differs");
     queries++;
    end
   end
   $display("NATIVE165 frames=%0d captured=%0d banks=%0d complete=%0d partial=%0d empty=%0d queries=%0d cpu=%0d ppu=%0d pixel=%h bus=%h",frame,captured,bank_changes,complete_tiles,partial_tiles,empty_tiles,queries,cpu_reads,ppu_reads,pixel_hash,bus_hash);
   // A real boot prefix need not switch an already sampled logical slot.
   // Missing rows are a measured limitation, not invented coverage.
   if(!control && (captured<1000 || complete_tiles+partial_tiles<1))$fatal(1,"actual game CHR coverage absent");
   @(negedge clk);native_release_cache=1;@(negedge clk);native_release_cache=0;
   if(native_owned)$fatal(1,"release failed");
   repeat(512)@(negedge clk);
   if(rom_fault)$fatal(1,"game fault after cache release");
   $display("PASS NATIVE165 actual PPU binding control=%0d",control);$finish;
  end
 endtask
