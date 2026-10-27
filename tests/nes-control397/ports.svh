// SPDX-License-Identifier: MIT
// Passive clock/port census. No DUT assignment, credit or timeline change.
 integer trace397;initial trace397=$fopen("ports397.csv","w");
 reg [15:0] last_n397=0,last_h397=0;integer last_nf397=0,last_hf397=0,last_hstate397=-1;
 wire source_write397=dut.core.transport.source_live&&((dut.core.transport.footer_busy&&source_capture396)||
  (dut.core.transport.byte_valid&&dut.core.transport.byte_ready));
 wire [15:0] nes_flags397={3'd0,frame.identity_pending,frame.materialized,source_owned365,
  dut.core.transport.record_valid&&!dut.core.transport.record_ready,dut.core.transport.full,
  dut.core.transport.crc_pending,planrom.source.tile_request&&!planrom.source.tile_ready,
  planrom.transport.plan_capture396,source_request396,
  planrom.transport.plan_request396,source_write397,tv263&&!tr263,source_capture396};
 wire host_qread397=dut.flow.state==dut.flow.HREAD||dut.flow.state==dut.flow.RREAD||dut.flow.state==dut.flow.GET||dut.flow.state==dut.flow.MREAD;
 wire [15:0] host_flags397={5'd0,dut.flow.aperture.binding&&dut.flow.aperture.ps==0,
  dut.flow.aperture.copy_write,dut.flow.meta_write396,spi_front270.byte_event,
  dut.flow.footer_active396,dut.flow.capture,host_qread397,dut.flow.canonical_write,
  dut.flow.queue.write312,dut.flow.aperture_put&&dut.flow.put_ready,
  dut.flow.word_valid&&dut.flow.word_ready};
 always @(posedge clk)if(!reset&&f>=905)begin
  if(f!=last_nf397||nes_flags397!=last_n397)begin
   $fwrite(trace397,"nes,%0d,%0d,%0d,%0d,%0d,%0d,%0t\n",f,source_frame367,nes_flags397,
    dut.core.transport.wbin,dut.core.transport.rbin,planrom.transport.state,$time);
   last_n397=nes_flags397;last_nf397=f;
  end
  if(release_frame||materialized366||source_done)
   if(release_frame||materialized366)$fwrite(trace397,"capture,%0d,%0d,%0d,%0d,%0d,%0t\n",f,source_frame367,release_frame,materialized366,owned,$time);
 end
 always @(posedge host_clk)if(!reset&&f>=905)begin
  if(f!=last_hf397||host_flags397!=last_h397||dut.flow.state!=last_hstate397)begin
   $fwrite(trace397,"host,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0t\n",f,host_flags397,dut.flow.state,
    dut.flow.aperture.used,dut.flow.aperture.stamps,dut.flow.queue.accepted,dut.flow.queue.retired,
    dut.flow.region,$time);
   last_h397=host_flags397;last_hstate397=dut.flow.state;last_hf397=f;
  end
  if(spi_front270.link[109])$fwrite(trace397,"SS_end,%0d,%0d,%0d,%0t\n",f,spi_front270.command,spi_front270.count,$time);
  if(spi_front270.byte_event&&spi_front270.count==0)$fwrite(trace397,"command,%0d,%0d,%0t\n",f,spi_front270.incoming,$time);
 end
 reg[63:0] last_hint397=0;
 wire[63:0] hint_flags397={planrom.hint.cursor,planrom.hint.running,planrom.hint.pending,planrom.hint.owner,
  prelease365,lease_valid,planrom.source.cache_path.cache.state,planrom.source.cache_path.cache.pending,
  planrom.source.cache_path.cache.back_request,planrom.source.arb_ready,qualify267,core_req267};
 always @(posedge clk)if(!reset&&f>=907)begin
  if(hint_flags397!=last_hint397&&(planrom.hint.running||planrom.hint.busy||last_hint397!=0))begin
   if(planrom.hint.running||planrom.hint.busy)
    $fwrite(trace397,"hint,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0t\n",f,
     planrom.hint.cursor,planrom.hint.running,planrom.hint.pending,planrom.hint.owner,
     planrom.source.cache_path.cache.state,planrom.source.cache_path.cache.pending,
     planrom.source.cache_path.cache.back_request,planrom.source.arb_ready,qualify267,core_req267,romcycle267,$time);
   last_hint397=hint_flags397;
  end
  if(planrom.hint.running&&planrom.mr&&planrom.mready&&!core_req267)
   $fwrite(trace397,"hint_grant,%0d,%0d,%0d,%0d,%0t\n",f,planrom.hint.cursor,planrom.ma,romcycle267,$time);
  if(planrom.hint.finished)$fwrite(trace397,"hint_done,%0d,%0d,%0t\n",f,romcycle267,$time);
 end
 final begin $fwrite(trace397,"end,%0d,%0t\n",f,$time);$fclose(trace397);end
