 // Record oracle times on the actual NES/host handshakes, before the
 // monitor synchronizers. Compare the serialized bytes, including wrap.
 reg first=0,head=0,retire=0,show=0,dma=0,query=0;
 reg [7:0] op=0,opcode=0;
 reg [4:0] idx=31;
 wire [7:0] data_out;
 reg [31:0] returned_token;
 nes_display1010 trace(.clk(host),.reset(reset),.active(1'b1),.cancel(stop),
  .first_e9(first),.writer(writer),.returned(consume),.tile_done(src.evt905[2]),
  .edge1027({bulk.edge1027[1] && scenario!=6,bulk.edge1027[0],src.evt905[1:0]}),
  .head_snapshot(consume && (scenario!=5 || token!=LAST)),
  .token(returned_token),.generation(GEN),.header(head),.data(opcode),
  .retired(retire),.op(op),.dma(dma),.show(show),.query(query),.index(idx),.reply(data_out));
 integer nt=0,groups=0,request_time=-1,grant_time=-1,group_time=-1,done_time=-1,end_time=-1,snapshot_time=-1;

 always @(posedge nes)begin
  if(!reset && pv && permit && ready)begin
   if(nt==0 || nt==1 || nt==4 || nt==5 || nt==7 || nt==14 || nt==19)begin
    groups++; group_time=trace.clock_count[30:15];request_time=-1;grant_time=-1;
   end
   nt++;
  end
  if(src.ahead.foreground && request_time<0)request_time=trace.clock_count[30:15];
  if(src.ahead.foreground && src.shared_ready && grant_time<0)grant_time=trace.clock_count[30:15];
  if(done)done_time=trace.clock_count[30:15];
  if(finish&&ender)end_time=trace.clock_count[30:15];
 end
 always @(posedge host) if(consume)begin
  snapshot_time=trace.clock_count[30:15];returned_token<=token;
 end
 task h;@(negedge host);endtask
 initial begin
  wait(!reset);repeat(6)h;
  // Prime a previous display and cross the low-eight timestamp wrap.
  trace.clock_count=31'd8355800;
  op=1;retire=1;h;retire=0;opcode=3;head=1;h;head=0;dma=1;h;dma=0;
  show=1;h;show=0;op=3;retire=1;h;retire=0;
  first=1;h;first=0;op=1;retire=1;h;retire=0;
 end
 function automatic bit stamp_matches(input [7:0] actual,input integer edge_time);
  return edge_time>=0 && (actual==edge_time[7:0] || actual==8'(edge_time+1));
 endfunction
 reg [7:0] bytes_out[0:31];
 task inspect_header;
  integer i;
  repeat(10)h;opcode=3;head=1;h;head=0;dma=1;h;dma=0;
  show=1;h;show=0;op=3;retire=1;h;retire=0;h;query=1;h;query=0;
  for(i=0;i<32;i++)begin idx=i;repeat(3)h;bytes_out[i]=data_out;end
  if(groups!=7 || nt!=22 || bytes_out[1]!=8'ha1 || {bytes_out[3],bytes_out[2]}!==GEN ||
     bytes_out[4]!==22 || bytes_out[5]!==7 || {bytes_out[15],bytes_out[14],bytes_out[13],bytes_out[12]}!==LAST ||
     bytes_out[30]!==15 || bytes_out[31]!==((scenario==5 || scenario==6)?0:165) || bytes_out[9][7:6]!==3 ||
     !stamp_matches(bytes_out[26],group_time) || !stamp_matches(bytes_out[27],done_time) ||
     (scenario!=6 && !stamp_matches(bytes_out[28],end_time)) || (scenario!=5 && !stamp_matches(bytes_out[29],snapshot_time)) ||
     !stamp_matches(bytes_out[10],request_time) || !stamp_matches(bytes_out[11],grant_time))
   $fatal(1,"header/identity mismatch groups=%0d tiles=%0d flags=%02h footer=%02h",groups,nt,bytes_out[30],bytes_out[31]);
  $display("PASS1027 group=%0d request=%0d grant=%0d done=%0d end=%0d head_E8=%0d",group_time,request_time,grant_time,done_time,end_time,snapshot_time);
  $write("HEADER1027 ");for(i=0;i<32;i++)$write("%02x",bytes_out[i]);$display("");
 endtask
