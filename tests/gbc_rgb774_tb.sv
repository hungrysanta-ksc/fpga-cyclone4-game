`timescale 1ns/1ps
module gbc_rgb774_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,start=0,pv=0;reg[14:0]rgb=0;
 wire armed,error,req,wr;wire[3:0]code;wire[6:0]level;
 wire[22:0]addr;wire[15:0]data;
 reg ack=0;reg[15:0]rdata=0;reg pending=0,pwrite;
 reg[22:0]paddr;reg[15:0]pdata;integer delay_left=0,cycle=0;
 reg[15:0]mem[0:262143];
 // Reserve a CPU access each 16 clocks and exclude the fourth-cycle
 // cart guard on writes. These are synthetic contenders, not a CPU trace.
 wire allowed=(cycle%16>=5)&&!(wr&&cycle%4==0);
 wire accept=!pending&&allowed;
 wire wv,palv,pali,done;wire[1:0]bank;wire[4:0]stage;wire[23:0]ctx;wire[15:0]wa;wire[14:0]palrgb;wire[15:0]wd;
 wire[7:0]palrow;wire[5:0]palslot;
 wire wok=cycle%4==0,palok=cycle%3==0;
 frame_pipeline_ring3 dut(clk,reset,start,1'b1,pv,rgb,armed,level,error,code,
 req,wr,addr,data,accept,ack,rdata,wv,wok,wa,wd,palv,palok,pali,palrow,palslot,palrgb,done,bank,stage,ctx);
 reg[15:0]output_words[0:8639];reg[8639:0]seen=0; reg[15:0]low_words[0:5759];reg[5759:0]low_seen=0;
 reg[14:0]initial_colors[0:63],event_colors[0:1007],live_colors[0:63];
 reg[5:0]event_slots[0:1007];integer event_counts[0:143];
 reg[14:0]file_pixels[0:23039];string vec;
 integer frames=0,pixels=0,word_count=0,pal_count=0,peak=0,begin_cycle=0,max_cycles=0,overlap=0,dummy;
 integer idx,slot,evt;
 function automatic[14:0]expected(input integer f,p);
  if(vec!="")expected=file_pixels[p] ^ ((f&1)?15'h0421:15'h0000);
  else expected=15'h100+f*64+1+(((p/160)/(12+f))%8)*4+(p%4);
 endfunction
 function automatic [14:0]unpack_low(input integer posn);
  integer x,y,at,bit_at; reg[3:0]n;
  begin
   x=posn%160;y=posn/160;bit_at=7-(x%8);
   at=((y/8)*20+x/8)*16+y%8;
   n={low_words[at+8][8+bit_at],low_words[at+8][bit_at],low_words[at][8+bit_at],low_words[at][bit_at]};
   unpack_low={4'b0,n[3],3'b0,n[2:1],4'b0,n[0]};
  end
 endfunction
 task automatic tick(input integer n);repeat(n)@(negedge clk);endtask
 // Optional bridge to the SNES pixel test, using the actual RTL output.
 string output_prefix;
 task automatic export_frame;
  integer pal_fd, plane_fd, low_fd;
  if (frames==0 && $value$plusargs("EXPORT=%s",output_prefix)) begin
   pal_fd=$fopen({output_prefix,".pal"},"w");
   plane_fd=$fopen({output_prefix,".planes"},"w");
   low_fd=$fopen({output_prefix,".low"},"w");
   if (!pal_fd || !plane_fd || !low_fd) $fatal(1,"cannot open output");
   for(integer s=0;s<64;s++) $fdisplay(pal_fd,"-1 %0d %0d",s,initial_colors[s]);
   for(integer y=0;y<143;y++)
    for(integer e=0;e<event_counts[y];e++)
     $fdisplay(pal_fd,"%0d %0d %0d",y,event_slots[y*7+e],event_colors[y*7+e]);
   for(integer i=0;i<8640;i++) $fdisplay(plane_fd,"%04h",output_words[i]);
   for(integer i=0;i<5760;i++) $fdisplay(low_fd,"%04h",low_words[i]);
   $fclose(pal_fd); $fclose(plane_fd); $fclose(low_fd);
  end
 endtask
 task automatic verify_frame;
  for(integer s=0;s<64;s=s+1)live_colors[s]=initial_colors[s];
  for(integer y=0;y<144;y=y+1)begin
   if(y>0)for(integer e=0;e<event_counts[y-1];e=e+1)
    live_colors[event_slots[(y-1)*7+e]]=event_colors[(y-1)*7+e];
   for(integer x=0;x<160;x=x+1)begin
    slot=0;
    for(integer pair=0;pair<3;pair=pair+1)begin
     idx=pair*2880+(y%8)*360+(y/8)*20+x/8;
     slot=slot|(((output_words[idx]>>(7-x%8))&1)<<(pair*2));
     slot=slot|(((output_words[idx]>>(15-x%8))&1)<<(pair*2+1));
    end
    if((live_colors[slot] + unpack_low(y*160+x))!==expected(frames,y*160+x))
     $fatal(1,"RGB_MISMATCH frame=%0d x=%0d y=%0d actual=%h expected=%h",frames,x,y,live_colors[slot] + unpack_low(y*160+x),expected(frames,y*160+x));
    pixels=pixels+1;
   end
  end
 endtask
 always @(posedge clk)begin
  cycle<=cycle+1;ack<=0;
  if(error)$fatal(1,"pipeline error=%0d context=%h",code,ctx);
  if(dut.capture.engine.queued>peak)peak=dut.capture.engine.queued;
  if(dut.state==3)begin_cycle=cycle;
  if(dut.accepted[0]&&dut.cw&&dut.state!=0)overlap=overlap+1;
  if(reset)pending<=0;
  else if(pending)begin
   if(delay_left==0)begin
    if(pwrite)mem[paddr-23'h400000]<=pdata;else rdata<=mem[paddr-23'h400000];
    ack<=1;pending<=0;
   end else delay_left<=delay_left-1;
  end else if(req&&accept)begin
   if(addr<23'h400000||addr>23'h43ffff)$fatal(1,"MEMORY_RANGE");
   if(wr&&addr<23'h430000&&addr[15]&&dut.banks[addr[17:16]])$fatal(1,"OWNED_BANK_OVERWRITE");
   pending<=1;paddr<=addr;pdata<=data;pwrite<=wr;delay_left<=wr?3:2;
  end
  if(wv&&wok&&wa[15])begin
   if(wa[0] || wa[14:1]>=5760 || low_seen[wa[14:1]])$fatal(1,"BG2_ADDRESS");
   low_seen[wa[14:1]]=1;low_words[wa[14:1]]=wd;
  end else if(wv&&wok)begin
   if(wa>=17280||wa[0]||seen[wa/2])$fatal(1,"OUTPUT_ADDRESS");
   output_words[wa/2]=wd;seen[wa/2]=1;word_count=word_count+1;
  end
  if(palv&&palok)begin
   if(pali)begin initial_colors[palslot]=palrgb;pal_count=pal_count+1;end
   else begin
    if(palrow>=143||event_counts[palrow]>=7)$fatal(1,"EVENT_RANGE");
    evt=palrow*7+event_counts[palrow];event_slots[evt]=palslot;event_colors[evt]=palrgb;
    event_counts[palrow]=event_counts[palrow]+1;
   end
  end
  if(done)begin
   if(word_count!=8640||pal_count!=64||!(&seen)||!(&low_seen))$fatal(1,"INCOMPLETE_OUTPUT");
   verify_frame();
   export_frame();
   if(cycle-begin_cycle>max_cycles)max_cycles=cycle-begin_cycle;

   $display("FRAME_PASS frame=%0d cycles=%0d",frames,cycle-begin_cycle);
   frames=frames+1;seen=0;low_seen=0;word_count=0;pal_count=0;
   for(integer y=0;y<144;y=y+1)event_counts[y]=0;
  end
 end
 initial begin
  dummy=$value$plusargs("VECTORS=%s",vec);
  if(vec=="")$fatal(1,"+VECTORS=<23040 RGB555 hex words> required");
  $readmemh(vec,file_pixels);
  for(integer y=0;y<144;y=y+1)event_counts[y]=0;
  tick(5);reset=0;start=1;tick(1);start=0;wait(armed);tick(1);
  for(integer f=0;f<4;f=f+1)begin
   for(integer y=0;y<144;y=y+1)begin
    for(integer x=0;x<160;x=x+1)begin
     pv=1;rgb=expected(f,y*160+x);tick(1);pv=0;tick(7);
    end
    tick(2368);
   end
   tick(36480);
  end
  wait(frames==4);tick(3);

  $display("PASS FRAME_PIPELINE frames=%0d pixels=%0d max_cycles=%0d fifo_peak=%0d overlap_writes=%0d",frames,pixels,max_cycles,peak,overlap);
  $finish;
 end
 initial begin #110000000;$fatal(1,"TIMEOUT");end
endmodule
