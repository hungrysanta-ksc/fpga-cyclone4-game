`timescale 1ns/1ps
module patch_rows181_tb;
reg clk=0,reset=1,release_frame=0,begin_frame=0,end_frame=0,source_fault=0;
always #5 clk=~clk;
reg [15:0] generation_in=1,query_generation=1;
reg row_start=0,row_end=0,pixel_valid=0,need_patch=0,query=0;
reg [7:0] row_index=0,pixel_x=0,query_x=0;reg [5:0] pixel_color=0;reg [2:0] query_slot=0;
wire active,owned,valid,response,hit,row_commit,row_patched;wire [15:0] generation;
wire [7:0] errors,committed_row;wire [2:0] count,row_slot;wire [5:0] data;
nes_patch_rows181 dut(.*);
integer tests=0,reads=0,fd;reg dumping=0;
function automatic integer selected_row(input integer slot);
 case(slot)0:selected_row=0;1:selected_row=1;2:selected_row=7;3:selected_row=8;4:selected_row=185;5:selected_row=186;default:selected_row=223;endcase
endfunction
function automatic integer selected(input integer y);
 selected=(y==0||y==1||y==7||y==8||y==185||y==186||y==223);
endfunction
task tick;@(posedge clk);#1;@(negedge clk);endtask
task clear;
 release_frame=1;tick();release_frame=0;
 row_start=0;row_end=0;pixel_valid=0;need_patch=0;end_frame=0;source_fault=0;query=0;row_index=0;
 generation_in=generation_in+1;query_generation=generation_in;
 begin_frame=1;tick();begin_frame=0;
endtask
function automatic [5:0] color(input integer y,input integer x);
 color=(y*11+x*3+(x/7))&63;
endfunction
task line(input integer y,input integer patch_at,input integer omit);
 row_index=y;row_start=1;tick();row_start=0;
 for(integer x=0;x<256;x++)begin
  pixel_valid=(x!=omit);pixel_x=x;pixel_color=color(y,x);need_patch=(x==patch_at);tick();
  pixel_valid=0;need_patch=0;
  if(x%13==0)repeat(2)tick(); // core stalls do not duplicate pixels
 end
 row_end=1;tick();row_end=0;
endtask
task finish(input integer expected_errors,input integer expected_count);
 end_frame=1;tick();end_frame=0;
 if(!owned || active || errors!==expected_errors[7:0] || count!=expected_count || valid!==(expected_errors==0))
  $fatal(1,"finish err=%h expected=%h count=%0d valid=%b",errors,expected_errors,count,valid);
 tests=tests+1;
endtask
task read_row(input integer slot,input integer y);
 query_slot=slot;query=1;
 for(integer x=0;x<256;x++)begin
  query_x=x;tick();if(!response || !hit || data!==color(y,x))$fatal(1,"pixel slot=%0d row=%0d x=%0d data=%h",slot,y,x,data);
  reads=reads+1;
  if(dumping)$fwrite(fd,"%0d %0d %02x\n",y,x,data);
 end
 query=0;tick();if(hit || data!=0)$fatal(1,"stale response");
endtask
initial begin
 repeat(3)tick();reset=0;clear();
 // Real179 boundaries are at arbitrary dots; retaining an entire completed
 // row avoids needing a guessed blank color or losing pixels before trigger.
 for(integer y=0;y<224;y++)begin
  line(y,(y==0)?0:(y==185)?173:(y==186)?255:-1,-1);
  if(!row_commit || committed_row!=y || row_patched!==(y==0||y==185||y==186))$fatal(1,"descriptor");
 end
 finish(0,3);read_row(0,0);read_row(1,185);read_row(2,186);
 query=1;query_slot=3;tick();if(hit || data!=0)$fatal(1,"unretained scratch query");
 query_slot=0;query_generation=query_generation-1;tick();if(hit)$fatal(1,"generation query");query=0;
 clear();for(integer y=0;y<224;y++)line(y,-1,-1);finish(0,0);
 query=1;query_slot=0;tick();if(hit)$fatal(1,"prior payload leaked");query=0;
 clear();for(integer y=0;y<224;y++)line(y,selected(y)?(y*31)%256:-1,-1);finish(0,7);
 fd=$fopen("captured-rows.txt","w");dumping=1;
 for(integer slot=0;slot<7;slot++)read_row(slot,selected_row(slot));
 dumping=0;$fclose(fd);
 source_fault=1;query=1;query_slot=0;tick();source_fault=0;query=0;
 if(valid || hit || errors!=32)$fatal(1,"late source fault");tests=tests+1;
 clear();for(integer y=0;y<224;y++)line(y,y<8?100:-1,-1);finish(8,7);
 query=1;query_slot=0;tick();if(hit)$fatal(1,"overflow frame visible");query=0;
 clear();for(integer y=0;y<224;y++)line(y,y==185?50:-1,y==185?42:-1);finish(23,0);
 // Fault/STOP does not wait for end of row or reset any RAM payload.
 clear();row_start=1;tick();row_start=0;source_fault=1;tick();source_fault=0;
 if(!owned || valid || errors!=32)$fatal(1,"fault retirement");tests=tests+1;
 clear();line(0,50,-1);release_frame=1;query=1;tick();release_frame=0;query=0;
 if(active||owned||valid||hit||count)$fatal(1,"release");tests=tests+1;
 begin_frame=1;source_fault=1;tick();begin_frame=0;source_fault=0;
 if(active||!owned||valid||errors!=32)$fatal(1,"begin fault");tests=tests+1;
 $display("PASS PATCH181 cases=%0d exact_pixels=%0d",tests,reads);$finish;
end
initial begin #20000000;$fatal(1,"watchdog");end
endmodule
