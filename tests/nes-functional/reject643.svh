 parameter integer GEN643=97;
 wire export_tx;
 reg offer_next=0;
 integer drops=0;
 always @(posedge nes)if(export_drop)drops++;
 always @(posedge lease_fault)$display("lease fault at %0.3f ns; current=%0d next=%0d export_error=%0d waiting=%b",
    $realtime,captured_gen,gen,export_reason,owner.waiting_display);
 nes_native_export203 exporter(.clk(nes),.reset(reset),
  .enable((owner.export_permitted||(lease&&dut.plan_closed))&&!nf),
  .start_permitted(owner.export_permitted||drained),
`ifdef DEFER643
  .discard_permitted(owner.export_permitted),
`endif
  .frame_owned(owned && offer_next),.geometry_valid(!reject_geometry),.frame_generation(gen),
  .patch_count(3'd0),.row_count(8'd224),.object_count(8'd0),.exception_count(8'd0),
  .group_count(reject_geometry?6'd0:6'd1),.palette_count(reject_geometry?6'd0:6'd1),.release_frame(export_drop),.error(export_reason),
  .response(1'b0),.hit(1'b0),.data(64'd0),.tx_ready(1'b1),.tx_valid(export_tx),
  .ack_valid(1'b0),.ack_accept(1'b0),.ack_generation(16'd0),.ack_ready(),.query(),.query_kind(),
  .query_index(),.query_generation(),.tx_data(),.busy(),.observe_state177());
 initial begin : stage_transition
  reg [7:0] tx[0:6],c,v;
  reg [159:0] reply;
  repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
  gen=GEN643-1;capture_begin=1;@(negedge nes);capture_begin=0;gen=GEN643;owned=1;
  @(negedge nes);release_frame=1;@(negedge nes);release_frame=0;owned=0;
  if(lease!==1 || captured_gen!==GEN643)$fatal(1,"current display lease");
  batch('h82,GEN643,0);status197();
  @(negedge nes);capture_begin=1;@(negedge nes);capture_begin=0;gen=GEN643+1;
  reject_geometry=1;owned=1;offer_next=1;
  batch('h83,GEN643,0);status197();
  for(int i=0;i<20;i++)reply[159-8*i-:8]=rx197[i];
  $display("WIRE643 %040h",reply);
  $display("RESULT643 gen=%0d E8 flags=%02h sent=%0d masks=%02h/%02h drops=%0d fault=%b",
   GEN643,rx197[3],rx197[5],rx197[14],rx197[15],drops,lease_fault);
`ifdef DEFER643
  if(rx197[3]!==2 || rx197[6]!==1 || rx197[8]!==32 || drops!=0 || lease!==1 || lease_fault!==0 || export_tx!==0)
   $fatal(1,"bad next input affected current END");
  for(int i=0;i<32;i++)begin
   @(negedge host);addr='h400800+i;rd_n=0;repeat(8)@(negedge host);
   if(oe!==0 || dout!==0)$fatal(1,"read");rd_n=1;repeat(8)@(negedge host);
  end
  for(int i=0;i<4;i++)write_bus('h604c+i,rx197[14+i]);
  write_bus('h6050,'ha5);status197();
  if(rx197[6]!==0 || lease!==1 || drops!=0)$fatal(1,"consume");
  tx[0]='hea;tx[1]=GEN643;tx[2]=0;tx[3]=0;tx[4]=2;c=0;
  for(int i=0;i<5;i++)c=crc8_197(c,tx[i]);
  tx[5]=c;tx[6]='ha5;
  fork
   begin begin197();foreach(tx[i])byte197(tx[i],v);end197();end
   begin wait(export_drop);if(lease!==0 || export_reason!==2 || export_tx!==0)$fatal(1,"bad discard");
    @(negedge nes);@(posedge nes);@(negedge nes);owned=0;end
  join
  status197();if(drops!=1 || lease_fault!==0 || hf!==0 || rx197[3]!==1 || rx197[5]!==0)$fatal(1,"rearm");
  @(negedge nes);capture_begin=1;@(negedge nes);capture_begin=0;gen=GEN643+2;reject_geometry=0;owned=1;
  wait(export_tx);if(export_reason!==0 || lease_fault!==0 || exporter.generation!==GEN643+2)$fatal(1,"fresh export");
`else
  if(lease_fault!==1 || hf!==1 || drops!=1 || export_reason!==2 || !rx197[3][7] ||
     rx197[5]!==2 || rx197[14]!==0 || !(rx197[15]===8'h24 || rx197[15]===8'h20))$fatal(1,"wrong origin");
  if(HOST_PHASE==8 && reply!==160'h00d70480000200000000000000000024000000c1)$fatal(1,"physical E8 mismatch");
`endif
  reset=1;addr='h6040;rd_n=0;repeat(12)@(negedge nes);
  if(lease!==0 || hf!==0 || nf!==0 || retire!==0 || oe!==1)$fatal(1,"STOP");
  $display("PASS643 gen=%0d STOP",GEN643);$finish;
 end
