// SPDX-License-Identifier: MIT
// Passive observation only. Never drives a DUT input or changes a test wait.
integer trace403,ht403=0,nt403=0;
integer h403[905:916][0:23],n403[905:916][0:15];
integer io403[905:916][0:255],wait403[905:916][0:255];
integer read403[905:916][0:223],write403[905:916][0:223];
integer command403[0:255],changed403[0:255];
integer last_header403=-1,min_header403=2147483647;
integer last_ppu403=-1,min_ppu403=2147483647;
reg changed_tx403=0;reg[5:0]lease_last403=0;
wire[5:0]lease_flags403={frame.capturing,frame.armed,frame.started,frame.materialized,frame.committed,frame.display_valid};
initial begin
 trace403=$fopen("extra403.csv","w");
 for(integer a403=0;a403<256;a403++)begin command403[a403]=0;changed403[a403]=0;end
 for(integer f403=905;f403<=916;f403++)begin
  for(integer j403=0;j403<24;j403++)h403[f403][j403]=0;
  for(integer j403=0;j403<16;j403++)n403[f403][j403]=0;
  for(integer j403=0;j403<256;j403++)begin io403[f403][j403]=0;wait403[f403][j403]=0;end
  for(integer j403=0;j403<224;j403++)begin read403[f403][j403]=0;write403[f403][j403]=0;end
 end
end
always @(posedge host_clk)begin
 ht403++;
 if(!reset&&f>=905&&f<=916)begin
  if(dut.flow.io_fire)begin
   io403[f][dut.flow.ioa]++;
   if(dut.flow.ioa==43||dut.flow.ioa==45||dut.flow.ioa==48||dut.flow.ioa==56||dut.flow.ioa==59||dut.flow.ioa==62)
    $fwrite(trace403,"io,%0d,%0d,%0d,%0d,%0d,%0d,%0t\n",f,dut.flow.ioa,dut.flow.iow,dut.flow.debug_pc,dut.flow.chunk_token,dut.flow.chunk_length,$time);
  end
  if(dut.flow.iov&&!dut.flow.ioready)wait403[f][dut.flow.ioa]++;
  if(dut.flow.core_grant)begin
   if(dut.flow.mw)write403[f][dut.flow.ma]++;else read403[f][dut.flow.ma]++;
  end
  if(dut.flow.aperture.ordinary_write)h403[f][0]++;
  if(dut.flow.aperture.copy_write)h403[f][1]++;
  if(dut.flow.aperture.binding)h403[f][2]++;
  if(dut.flow.aperture.ps==dut.flow.aperture.P_READ)h403[f][3]++;
  if(dut.flow.aperture.bs==dut.flow.aperture.B_READ)h403[f][4]++;
  if(dut.flow.aperture.bs==dut.flow.aperture.B_CAP)h403[f][5]++;
  if(dut.flow.aperture.ordinary_write&&dut.flow.core_grant)h403[f][6]++;
  if(dut.flow.tag_write400)h403[f][7]++;
  if(dut.flow.tag_grant400)h403[f][8]++;
  if(dut.flow.tag_write400&&!dut.flow.tag_ready400)h403[f][9]++;
  if(planrom.transport.write_valid&&planrom.transport.write_ready)h403[f][10]++;
  if(dut.flow.core_grant&&planrom.transport.write_valid&&planrom.transport.write_ready)h403[f][11]++;
  if(dut.flow.header_grant)begin
   if(last_header403>=0&&ht403-last_header403<min_header403)min_header403=ht403-last_header403;
   last_header403=ht403;
  end
  if(!spi_front270.ss[1])begin
   if(spi_front270.live_key331!=spi_front270.progress_key331)begin
    h403[f][12]++;
    if(!changed_tx403)begin changed403[spi_front270.command]++;changed_tx403=1;
     $fwrite(trace403,"snapshot_change,%0d,%0d,%0d,%0t\n",f,spi_front270.command,spi_front270.count,$time);
    end
   end
   if(spi_front270.byte_event&&spi_front270.count==0)begin
    command403[spi_front270.incoming]++;changed_tx403=0;
   end
  end else changed_tx403=0;
  if(dut.flow.aperture.prefill_commit&&dut.flow.aperture.take_tile)h403[f][13]++;
  if(dut.flow.open398&&!dut.flow.begin_ready)h403[f][14]++;
  if(dut.flow.put398&&!dut.flow.put_ready)h403[f][15]++;
 end
end
always @(posedge clk)begin
 nt403++;
 if(!reset&&f>=905&&f<=916)begin
  if(frame.capturing&&frame.display_valid)n403[f][0]++;
  if(frame.armed&&frame.display_valid)n403[f][1]++;
  if(frame.materialized&&frame.display_valid)n403[f][2]++;
  if(frame.committed&&frame.display_valid)n403[f][3]++;
  if(frame.frame.raster.line_start)n403[f][4]++;
  if(frame.frame.raster.midline)n403[f][5]++;
  if(frame.frame.raster.copy_busy)n403[f][6]++;
  if(frame.frame.raster.row_commit)n403[f][7]++;
  if(frame.frame.raster.midline&&frame.frame.raster.palette!=frame.frame.raster.line_palette)n403[f][8]++;
  if(frame.frame.raster.line_start||frame.frame.raster.midline)begin
   if(last_ppu403>=0&&nt403-last_ppu403<min_ppu403)min_ppu403=nt403-last_ppu403;
   last_ppu403=nt403;
  end
  if(lease_flags403!=lease_last403)begin
   $fwrite(trace403,"lease,%0d,%0d,%0d,%0d,%0d,%0d,%0t\n",f,source_frame367,lease_flags403,frame.source_serial,frame.display_serial373,frame.source_generation,$time);
   lease_last403=lease_flags403;
  end
 end
end
final begin
 for(integer f403=905;f403<=916;f403++)begin
  for(integer j403=0;j403<24;j403++)$fwrite(trace403,"host,%0d,%0d,%0d\n",f403,j403,h403[f403][j403]);
  for(integer j403=0;j403<16;j403++)$fwrite(trace403,"NES,%0d,%0d,%0d\n",f403,j403,n403[f403][j403]);
  for(integer j403=0;j403<256;j403++)begin
   $fwrite(trace403,"IO,%0d,%0d,%0d,%0d\n",f403,j403,io403[f403][j403],wait403[f403][j403]);
   if(j403<224)$fwrite(trace403,"context,%0d,%0d,%0d,%0d\n",f403,j403,read403[f403][j403],write403[f403][j403]);
  end
 end
 for(integer j403=0;j403<256;j403++)if(command403[j403]||changed403[j403])$fwrite(trace403,"SPI,%0d,%0d,%0d\n",j403,command403[j403],changed403[j403]);
 $fwrite(trace403,"minimum_header_host_clocks,%0d\nminimum_palette_sample_NES_clocks,%0d\n",min_header403,min_ppu403);
 $fclose(trace403);
end
