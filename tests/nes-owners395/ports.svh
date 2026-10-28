// SPDX-License-Identifier: MIT
// Passive evidence only. No DUT assignments, delay changes or new credits.
 integer trace395;initial trace395=$fopen("ports395.csv","w");
 integer nf395=0,hf395=0;reg [3:0] np395=0;reg [5:0] hp395=0;
 wire nw395=dut.core.transport.source_live&&(dut.core.transport.footer_busy||
  (dut.core.transport.byte_valid&&dut.core.transport.byte_ready));
 wire nr395=!planrom.transport.nr&&!planrom.transport.nc&&planrom.transport.state==planrom.transport.READ;
 wire [3:0] ns395={planrom.source.tile.busy&&planrom.source.tile.state==planrom.source.tile.WAIT,nr395,nw395,tv263&&!tr263};
 wire hq395=dut.flow.state==dut.flow.HREAD||dut.flow.state==dut.flow.RREAD||dut.flow.state==dut.flow.GET||dut.flow.state==dut.flow.MREAD;
 wire [5:0] hs395={dut.flow.word_ready&&dut.flow.word_valid,dut.flow.read359[33],
  dut.flow.aperture_put&&dut.flow.put_ready,hq395,dut.flow.canonical_write,dut.flow.queue.write312};
 always @(posedge clk)if(!reset&&f>=905)begin
  if(f!=nf395||ns395!=np395)begin $fwrite(trace395,"nes,%0d,%0d,%0t\n",f,ns395,$time);np395=ns395;nf395=f;end
  if(tv263&&tr263)$fwrite(trace395,"tile,%0d,%0d,%0d,%0d,%0t\n",f,tk263,ts263,ti263,$time);
 end
 always @(posedge host_clk)if(!reset&&f>=905)begin
  if(f!=hf395||hs395!=hp395)begin $fwrite(trace395,"host,%0d,%0d,%0t\n",f,hs395,$time);hp395=hs395;hf395=f;end
  if(dut.flow.state==dut.flow.RCHECK&&!dut.flow.bad_record)
   $fwrite(trace395,"record,%0d,%0d,%0d,%0d,%0t\n",f,dut.flow.region,dut.flow.canonical,dut.flow.decoded,$time);
 end
 final begin $fwrite(trace395,"end,%0d,%0t\n",f,$time);$fclose(trace395);end
