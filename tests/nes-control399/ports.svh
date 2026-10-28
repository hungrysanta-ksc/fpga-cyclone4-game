// SPDX-License-Identifier: MIT
// Passive 398 port/read/publication census. Never drives a DUT signal.
integer trace399;initial trace399=$fopen("ports399.csv","w");
integer hc399[905:916][0:31],nc399[905:916][0:15];
integer hf399,nf399;reg[2:0]last_phase399=7;reg[31:0]last_token399=0;
reg[18:0]last_source399=0;reg[15:0]last_w399=0,last_r399=0;
initial begin
 for(integer f399=905;f399<=916;f399++)begin
  for(integer i399=0;i399<32;i399++)hc399[f399][i399]=0;
  for(integer i399=0;i399<16;i399++)nc399[f399][i399]=0;
 end
end
wire source_write399=dut.core.transport.source_live&&((dut.core.transport.footer_busy&&source_capture396)||(dut.core.transport.byte_valid&&dut.core.transport.byte_ready));
wire[18:0]source_flags399={2'd0,frame.identity_pending,frame.materialized,source_owned365,
 dut.core.transport.record_valid&&!dut.core.transport.record_ready,dut.core.transport.full,
 dut.core.transport.crc_pending,planrom.source.tile_request&&!planrom.source.tile_ready,
 planrom.transport.plan_capture396,source_request396,planrom.transport.plan_request396,
 source_write399,tv263&&!tr263,source_capture396,planrom.hint.busy,lease_valid,prelease365,qualify267};
always @(posedge host_clk)if(!reset&&f>=905&&f<=916)begin
 hf399=f;
 hc399[hf399][0]++;
 if(dut.flow.read359[33])begin hc399[hf399][1]++;$fwrite(trace399,"read,%0d,%0d,%0d,%0d,%0t\n",f,dut.flow.read_count,dut.flow.tap_position,dut.flow.region,$time);end
 if(dut.flow.read_end&&dut.flow.ap>=24'h400800&&dut.flow.ap<24'h401800)hc399[hf399][2]++;
 if(dut.flow.read_pending)hc399[hf399][3]++;
 if(dut.flow.core_grant&&!dut.flow.mw)hc399[hf399][4]++;
 if(dut.flow.core_grant&&dut.flow.mw)hc399[hf399][5]++;
 if(dut.flow.mv&&!dut.flow.mready)hc399[hf399][6]++;
 if(dut.flow.header_grant)hc399[hf399][7]++;
 if(dut.flow.header_request&&!dut.flow.header_grant)hc399[hf399][8]++;
 if(dut.flow.stage_atomic)hc399[hf399][9]++;
 if(dut.flow.aperture.copy_write)hc399[hf399][10]++;
 if(dut.flow.stage_write)hc399[hf399][11]++;
 if(dut.flow.aperture.binding)hc399[hf399][12]++;
 if(dut.flow.aperture.prefill_commit)hc399[hf399][13]++;
 if(dut.flow.consume398)hc399[hf399][14]++;
 if(dut.flow.out398&&dut.flow.ioa==122)hc399[hf399][15]++;
 if(dut.flow.qretire)hc399[hf399][16]++;
 if(dut.flow.consume_record312)hc399[hf399][17]++;
 if(dut.flow.queue_irq398)hc399[hf399][18]++;
 if(dut.flow.handler)hc399[hf399][19]++;
 if(dut.flow.mv)hc399[hf399][20]++;
 if(dut.flow.iov)hc399[hf399][21]++;
 if(dut.flow.footer_request396)hc399[hf399][22]++;
 if(dut.flow.out398&&dut.flow.ioa==dut.flow.IO_OPEN)hc399[hf399][23]++;
 if(dut.flow.finish_pending)hc399[hf399][24]++;
 if(dut.flow.word_valid&&!dut.flow.word_ready)hc399[hf399][25]++;
 if(dut.flow.mv&&dut.flow.stage_atomic)hc399[hf399][26]++;
 if(dut.flow.header_request&&dut.flow.stage_atomic)hc399[hf399][27]++;
 if(dut.flow.capture&&!dut.flow.read359[33])hc399[hf399][28]++;
 if(dut.flow.out398&&dut.flow.ioa==dut.flow.IO_TAKE)hc399[hf399][29]++;
 if(dut.flow.phase!=last_phase399||dut.flow.chunk_token!=last_token399)begin
  $fwrite(trace399,"publication,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0t\n",f,dut.flow.phase,dut.flow.chunk_token,dut.flow.aperture.used,dut.flow.aperture.stamps,dut.flow.queue.accepted,dut.flow.queue.retired,$time);
  last_phase399=dut.flow.phase;last_token399=dut.flow.chunk_token;
 end
 if(dut.flow.read_end&&dut.flow.ap[23:8]==16'h0060)$fwrite(trace399,"control_read,%0d,%0d,%0t\n",f,dut.flow.ap,$time);
 if(spi_front270.link[109])$fwrite(trace399,"SS_end,%0d,%0d,%0d,%0t\n",f,spi_front270.command,spi_front270.count,$time);
end
always @(posedge clk)if(!reset&&f>=905&&f<=916)begin
 nf399=f;nc399[nf399][0]++;
 if(source_write399)nc399[nf399][1]++;
 if(source_request396)nc399[nf399][2]++;
 if(dut.core.transport.record_valid&&!dut.core.transport.record_ready)nc399[nf399][3]++;
 if(planrom.transport.plan_request396)nc399[nf399][4]++;
 if(planrom.transport.plan_capture396)nc399[nf399][5]++;
 if(source_request396&&planrom.transport.plan_request396)nc399[nf399][6]++;
 if(source_capture396)nc399[nf399][7]++;
 if(tv263&&!tr263)nc399[nf399][8]++;
 if(qualify267)nc399[nf399][9]++;
 if(planrom.mr&&planrom.mready)begin
  nc399[nf399][10]++;
  if(planrom.ha361)nc399[nf399][11]++;else nc399[nf399][12]++;
  $fwrite(trace399,"ROM_grant,%0d,%0d,%0d,%0d,%0d,%0t\n",f,source_frame367,planrom.ha361,planrom.ma,romcycle267,$time);
 end
 if(core_req267)nc399[nf399][13]++;
 if(hint_metaactive398)nc399[nf399][14]++;
 if(source_flags399!=last_source399||dut.core.transport.wbin!=last_w399||dut.core.transport.rbin!=last_r399)begin
  $fwrite(trace399,"source,%0d,%0d,%0d,%0d,%0d,%0d,%0t\n",f,source_frame367,source_flags399,dut.core.transport.wbin,dut.core.transport.rbin,planrom.transport.state,$time);
  last_source399=source_flags399;last_w399=dut.core.transport.wbin;last_r399=dut.core.transport.rbin;
 end
end
final begin
 for(integer f399=905;f399<=916;f399++)begin
  for(integer i399=0;i399<32;i399++)$fwrite(trace399,"host_count,%0d,%0d,%0d\n",f399,i399,hc399[f399][i399]);
  for(integer i399=0;i399<16;i399++)$fwrite(trace399,"NES_count,%0d,%0d,%0d\n",f399,i399,nc399[f399][i399]);
 end
 $fclose(trace399);
end
