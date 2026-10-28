// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module capture402_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,release_scene=0,begin_scene=0,end_scene=0,source_fault=0,event_valid=0,row_commit=0,row_patched=0,query=0;
 reg[63:0]event_data=0;reg[7:0]committed_row=0;reg[1:0]query_kind=0;reg[10:0]query_address=0;
 wire[1:0]active,owned,valid,response,hit,patch;wire[7:0]errors[2],rows[2],objects[2],exceptions[2];wire[5:0]groups[2];wire[63:0]data[2];
 nes_native_compact402_reference ref402(.clk(clk),.reset(reset),.release_scene(release_scene),.begin_scene(begin_scene),.end_scene(end_scene),.source_fault(source_fault),
 .event_valid(event_valid),.event_data(event_data),.row_commit(row_commit),.row_patched(row_patched),.committed_row(committed_row),.row_needs_patch(patch[0]),
 .query(query),.query_kind(query_kind),.query_address(query_address),.active(active[0]),.owned(owned[0]),.valid(valid[0]),.errors(errors[0]),.row_count(rows[0]),.object_count(objects[0]),.exception_count(exceptions[0]),.group_count(groups[0]),.response(response[0]),.hit(hit[0]),.data(data[0]));
 nes_native_compact181 dut(.clk(clk),.reset(reset),.release_scene(release_scene),.begin_scene(begin_scene),.end_scene(end_scene),.source_fault(source_fault),
 .event_valid(event_valid),.event_data(event_data),.row_commit(row_commit),.row_patched(row_patched),.committed_row(committed_row),.row_needs_patch(patch[1]),
 .query(query),.query_kind(query_kind),.query_address(query_address),.active(active[1]),.owned(owned[1]),.valid(valid[1]),.errors(errors[1]),.row_count(rows[1]),.object_count(objects[1]),.exception_count(exceptions[1]),.group_count(groups[1]),.response(response[1]),.hit(hit[1]),.data(data[1]));
 integer events402=0,reads402=0,frames402=0;
 function automatic[63:0]cell402(input integer row,col,isobj,rank,fine,tile);
 reg[63:0]v;begin v=0;v[12:0]=tile;v[15:13]=isobj&&(tile&1)?7-fine:fine;v[32:25]=row;v[40:33]=col;
 v[48:41]=isobj?((tile&1)?8'hc3:8'h20):0;v[49]=isobj;v[52:50]=rank;cell402=v;end endfunction
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task clear402;begin event_valid=0;row_commit=0;begin_scene=0;end_scene=0;release_scene=1;tick();tick();release_scene=0;tick();end endtask
 task push402(input[63:0]v);begin event_valid=1;event_data=v;events402++;tick();end endtask
 task frame402(input integer salt,patch_mode);begin
  clear402();begin_scene=1;tick();begin_scene=0;tick();
  for(integer row=0;row<224;row++)begin
   for(integer col=0;col<33;col++)begin
    if(!(patch_mode&&(row==3||row==5)&&col==17))begin
     if(patch_mode&&row%5==1&&col==7)push402(cell402(row,col,0,0,row%8,100+col+salt)|(64'd1<<56)|(64'((row+1)%8)<<53));
     else push402(cell402(row,col,0,0,row%8,100+col+salt));
    end
   end
   if(row<112)begin
    push402(cell402(row*2,20,1,patch_mode==2?row%8:0,(row*2)%8,800+salt));
    push402(cell402(row*2+1,20,1,patch_mode==2?row%8:0,(row*2+1)%8,800+salt));
   end
   event_valid=0;row_commit=1;committed_row=row;row_patched=patch_mode&&(row==3||row==5);
   if(patch[0]!==patch[1]||patch[0]!==row_patched)$fatal(1,"raw row verdict402 row%0d ref%b candidate%b",row,patch[0],patch[1]);
   tick();row_commit=0;row_patched=0;
   // The original contract allows33 independent copy clocks. No extra
   // delay is granted to hide the synchronous previous-row read.
   repeat(33)tick();
  end
  end_scene=1;tick();end_scene=0;repeat(4)tick();
  if(owned!=3||valid!=3||errors[0]!=0||errors[1]!=0||rows[0]!=224||rows[1]!=224||groups[0]!=groups[1]||objects[0]!=objects[1])
   $fatal(1,"frame402 metadata owned%b valid%b err%h/%h groups%0d/%0d objects%0d/%0d",owned,valid,errors[0],errors[1],groups[0],groups[1],objects[0],objects[1]);
  for(integer kind=0;kind<4;kind++)begin
   query_kind=kind;
   for(integer at=0;at<(kind==0?groups[0]*33:kind==1?224:kind==2?objects[0]:exceptions[0])+2;at++)begin
    query=1;query_address=at;tick();
    if(response!=3||hit[0]!==hit[1]||data[0]!==data[1])$fatal(1,"query402 kind%0d at%0d hit%b data%h/%h",kind,at,hit,data[0],data[1]);
    reads402++;
   end
  end
  query=0;tick();frames402++;
 end endtask
 reg[14:0]prev_before[33];reg[61:0]rank_before[8];
 initial begin
  repeat(3)tick();reset=0;frame402(0,0);
  clear402();begin_scene=1;tick();begin_scene=0;tick();
  push402(cell402(0,0,0,0,0,99));push402(cell402(0,20,1,0,0,700));
  event_valid=0;release_scene=1;tick();
  for(integer i=0;i<33;i++)prev_before[i]=dut.previous[i];
  for(integer i=0;i<8;i++)rank_before[i]=dut.rank402[i];
  repeat(256)begin tick();if(owned[1]||valid[1])$fatal(1,"late capture publish402");
   for(integer i=0;i<33;i++)if(prev_before[i]!==dut.previous[i])$fatal(1,"STOP previous write402");
   for(integer i=0;i<8;i++)if(rank_before[i]!==dut.rank402[i])$fatal(1,"STOP rank write402");
  end
  release_scene=0;frame402(7,0);frame402(0,0);frame402(5,1);frame402(3,2);
  $display("PASS CAPTURE402 frames=%0d events=%0d reads=%0d STOP=256",frames402,events402,reads402);$finish;
 end
 initial begin #5000000;$fatal(1,"capture402 timeout");end
endmodule
