// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module native_fill165_tb;
 parameter MODE=0;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,start=0,clear=0,frame_owned=1,geometry_valid=1;reg [15:0] frame_generation=41;
 wire query;wire [2:0] query_kind;wire [12:0] query_index;wire [15:0] query_generation;
 reg response=0,hit=0;reg [63:0] data=0;
 wire mem_ready,mem_request,mem_abort,mem_idle;reg mem_response=0,mem_error=0;
 wire [21:0] mem_address;wire [15:0] mem_generation;
 reg [21:0] mem_response_address=0;reg [15:0] mem_response_generation=0;reg [7:0] mem_data=0;
 wire byte_valid,byte_ready;wire [7:0] byte_data;wire [12:0] byte_tile;wire [3:0] byte_lane;
 wire [1:0] byte_kind;wire [15:0] byte_generation;
 wire busy,done,success,quarantine;wire [3:0] error;
 wire [9:0] tile_count;wire [13:0] byte_count;wire [31:0] cycles;
 nes_native_fill165 #(.MAX_TILES(MODE==7?1:512),.MAX_CYCLES(MODE==6?50:262144),.WAIT_CYCLES(32)) dut(.*);
 reg [1:0] required_set[0:8191];reg [7:0] chr[0:131071];
 reg model_pending=0;reg [21:0] saved_address;reg [15:0] saved_generation;
 integer ticks=0,delay_count=0,checks=0,requests=0,received=0,expected=0,index,output_file;
 integer last_tile=-1,last_lane=15;string required_name,chr_name,output_name;integer unused;
 assign mem_idle=!model_pending && !mem_response;
 assign mem_ready=(ticks%3!=0) && MODE!=12;
 assign byte_ready=(ticks%5!=0) && MODE!=11;
 task check(input bit condition,input string why);
  begin checks=checks+1;if(!condition)$fatal(1,"%s mode=%0d error=%0d state=%0d",why,MODE,error,dut.state);end
 endtask
 always @(posedge clk)begin
  ticks<=ticks+1;response<=0;hit<=0;data<=0;mem_response<=0;mem_error<=0;
  if(query)begin
   check(query_kind==6 && query_generation==frame_generation,"sealed query tag");
   if(MODE!=10)begin response<=1;hit<=MODE!=1;data<={62'd0,required_set[query_index]};end
  end
  if(mem_request && mem_ready)begin
   check(!model_pending,"one memory request outstanding");
   check(mem_address[21:17]==5'h10 && required_set[mem_address[16:4]]!=0,"physical required tile address");
   model_pending<=1;saved_address<=mem_address;saved_generation<=mem_generation;
   delay_count<=MODE==5?80:3+(mem_address[5:4]);requests<=requests+1;
  end
  if(model_pending)begin
   if(delay_count==0)begin
    model_pending<=0;mem_response<=1;mem_error<=MODE==4;
    mem_response_address<=saved_address^(MODE==2?22'd1:22'd0);
    mem_response_generation<=saved_generation+(MODE==3?1:0);
    mem_data<=chr[saved_address[16:0]];
   end else delay_count<=delay_count-1;
  end
  if(MODE==13 && busy && query)begin mem_response<=1;mem_response_address<=0;end
  if(byte_valid && byte_ready)begin
   check(!clear&&!reset&&!quarantine && geometry_valid && byte_generation==frame_generation,"stream lease");
   check(byte_kind==required_set[byte_tile] && byte_kind!=0 && byte_data===chr[{byte_tile,byte_lane}],"exact ROM bytes");
   if(byte_tile==last_tile)check(byte_lane==last_lane+1,"lane ordering");
   else check((last_tile<0 || byte_tile>last_tile) && last_lane==15 && byte_lane==0,"tile ordering");
   last_tile=byte_tile;last_lane=byte_lane;received<=received+1;
   $fwrite(output_file,"%0d %0d %0d %02h %0d\n",byte_generation,byte_tile,byte_lane,byte_data,byte_kind);
  end
 end
 initial begin
  unused=$value$plusargs("REQUIRED=%s",required_name);unused=$value$plusargs("CHR=%s",chr_name);
  unused=$value$plusargs("OUTPUT=%s",output_name);output_file=$fopen(output_name,"w");
  $readmemh(required_name,required_set);$readmemh(chr_name,chr);
  for(index=0;index<8192;index=index+1)if(required_set[index]!=0)expected=expected+16;
  repeat(3)@(negedge clk);reset=0;wait(!quarantine);@(negedge clk);start=1;@(negedge clk);start=0;
  if(MODE==8 || MODE==9 || MODE==14)begin
   wait(model_pending);@(negedge clk);
   if(MODE==8)clear=1;else if(MODE==14)reset=1;else frame_generation=frame_generation+1;
   @(negedge clk);clear=0;reset=0;
   check(quarantine&&mem_abort&&!byte_valid&&!mem_request,"cancelled pending request quarantined");
   if(MODE!=9)begin
    start=1;repeat(2)@(negedge clk);check(!busy,"cannot restart before backend flush");
    wait(!quarantine);wait(busy);@(negedge clk);start=0;
   end
  end
  wait(done);@(negedge clk);
  if(MODE==0 || MODE==8 || MODE==14 || MODE==15)begin
   check(success && error==0 && byte_count==expected && received==expected && tile_count==expected/16,"complete exact fill");
   if(MODE==15)begin
    geometry_valid=0;#1;check(!success,"completed data cannot outlive lease");
    repeat(2)@(negedge clk);geometry_valid=1;@(negedge clk);
    check(!success&&error==2,"revoked completion stays rejected");
   end
  end else begin
   check(!success && error!=0,"failure refuses commit");
   case(MODE)
    1:check(error==5,"lookup miss");2,3,4:check(error==7,"response address/tag/error");
    5,10,11,12:check(error==4,"finite wait");6:check(error==3,"total budget");
    7:check(error==6,"tile cap");9:check(error==2,"generation revocation");13:check(error==8,"unexpected reply");
   endcase
  end
  repeat(120)@(negedge clk);
  check(!mem_request&&!byte_valid&&!quarantine,"late reply drained without new data");
  $fclose(output_file);$display("PASS FILL165 mode=%0d checks=%0d requests=%0d bytes=%0d cycles=%0d",MODE,checks,requests,received,cycles);$finish;
 end
 initial begin #10000000;$fatal(1,"fill watchdog");end
endmodule
