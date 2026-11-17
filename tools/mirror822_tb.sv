`timescale 1ns/1ps
module mirror822_tb;
 reg clk=0,reset=1,stop=0,immutable=1,start=0,seal=0,release_bank=0,sample=0,request=0;
 reg [15:0] generation=0;
 reg [16:0] sample_address=0; reg [7:0] sample_data=0;
 reg [21:0] address=0;wire ready,response,error,back_request,start_ready,sample_ready;
 wire [21:0] back_address,response_address;wire [15:0] back_gen,response_generation;
 reg back_response=0;reg [7:0] expected;wire [7:0] data;
 always #5 clk=!clk;
 nes_chr_cache611 dut(.clk(clk),.reset(reset),.stop(stop),.immutable(immutable),
   .start(start),.seal(seal),.release_bank(release_bank),.capture_gen(generation),.release_gen(generation),
   .sample(sample),.sample_address(sample_address),.sample_data(sample_data),.start_ready(start_ready),.sample_ready(sample_ready),
   .request(request),.request_obj(1'b1),.address(address),.generation(generation),.ready(ready),.idle(),
   .response(response),.error(error),.data(data),.response_address(response_address),.response_generation(response_generation),
   .back_request(back_request),.back_abort(),.back_address(back_address),.back_generation(back_gen),.back_ready(1'b1),
   .back_idle(1'b1),.back_response(back_response),.back_error(1'b0),.back_response_address(address),
   .back_response_generation(generation),.back_data(expected));
 integer fd,outfd,op,v1,v2,v3,last_tick,code,found,seqid;
 initial begin
  fd=$fopen("stim.tsv","r");outfd=$fopen("hits.tsv","w");if(!fd||!outfd)$fatal;
  repeat(8) @(negedge clk);reset=0;
  while($fscanf(fd,"%d %d %d %d",op,v1,v2,v3)==4)begin
   case(op)
    0:begin seqid=v2;generation=v1;last_tick=0;#1;
      while(!start_ready)@(negedge clk);start=1;@(negedge clk);start=0;end
    1:begin repeat(v1-last_tick-1)@(negedge clk);last_tick=v1;
      if(!sample_ready)$fatal(1,"sample lost");sample=1;sample_address=v2;sample_data=v3;
      @(negedge clk);sample=0;end
    2:begin repeat(4)@(negedge clk);seal=1;@(negedge clk);seal=0;end
    3:begin address={5'h10,v1[16:0]};expected=v2;while(!ready)@(negedge clk);
      request=1;@(negedge clk);request=0;found=0;
      while(!response)begin
       if(back_request)begin found=2;if(back_address!=address||back_gen!=generation)$fatal;@(negedge clk);back_response=1;#1;end
       else begin found=1;@(negedge clk);end
      end
      if(data!==expected||error||response_address!=address||response_generation!=generation||(v3==1&&found!=0))$fatal(1,"lost original hit or data");
      $fdisplay(outfd,"%0d %0d %0d %0d",seqid,generation,v1,found);
      @(negedge clk);back_response=0;
    end
    4:begin release_bank=1;@(negedge clk);release_bank=0;end
   endcase
  end
  // Released generations cannot hit. Cancel between the first and alternate
  // lookup, then request the old key and require the backing ROM path.
  repeat(4)@(negedge clk);request=1;@(negedge clk);request=0;
  if(response)$fatal(1,"released generation");
  @(negedge clk);stop=1;#1;if(response||ready||back_request)$fatal;
  repeat(3)@(negedge clk);stop=0;while(!ready)@(negedge clk);
  request=1;@(negedge clk);request=0;
  while(!back_request)begin if(response)$fatal(1,"stale after STOP");@(negedge clk);end
  stop=1;#1;if(back_request||response)$fatal(1,"late backing request");
  $fclose(outfd);$display("PASS MIRROR822 primary hits, data, identities, STOP");$finish;
 end
 initial #100000000 $fatal(1,"timeout");
endmodule
