// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module native_chr165_tb;
 reg clk=0;always #23 clk=~clk;
 reg reset=1,sample=0,sample_valid=1,freeze=0,release_cache=0,query=0,query_obj4=0;
 reg [12:0] logical_address=0;reg [21:0] physical_address=0;reg [7:0] sample_data=0;
 reg [8:0] query_slot=0;reg [17:0] query_tag=0;reg [4:0] query_offset=0;
 wire initialized,owned,response,hit;wire [7:0] data;wire [15:0] valid_bytes;
 nes_native_chr165 dut(.*);
 reg [7:0] chr[0:131071];
 integer bank,tile,lane,off,checks=0,reads=0,negatives=0;
 task put(input integer logical_byte,input integer physical_byte,input integer value);
  begin @(negedge clk);logical_address=logical_byte;physical_address=physical_byte;
   sample_data=value;sample=1;@(posedge clk);#1;end
 endtask
 task lease;
  begin @(negedge clk);sample=0;freeze=1;wait(owned);@(negedge clk);freeze=0;end
 endtask
 task release_it;
  begin @(negedge clk);query=0;release_cache=1;@(negedge clk);release_cache=0;
   if(owned)$fatal(1,"release failed");end
 endtask
 task ask(input integer slot,input integer tag,input integer offset,input bit obj,
          input bit want_hit,input integer expected,input integer mask);
  begin @(negedge clk);query_slot=slot;query_tag=tag;query_offset=offset;query_obj4=obj;query=1;
   @(negedge clk);query=0;@(negedge clk);
   if(response!==1 || hit!==want_hit || data!==expected[7:0] || valid_bytes!==mask[15:0])
    $fatal(1,"query slot=%h tag=%h off=%d obj=%b response=%b hit=%b data=%h mask=%h expected=%h/%h",slot,tag,offset,obj,response,hit,data,valid_bytes,expected,mask);
   checks=checks+1;
  end
 endtask
 initial begin
  $readmemh("chr.hex",chr);
  repeat(3)@(negedge clk);reset=0;wait(initialized);
  // Invalid response, wrong byte offset and non-CHR memory must never enter.
  sample_valid=0;put(0,'h200000,99);sample_valid=1;
  put(0,'h200001,98);put(0,'h3a0000,97);lease();
  ask(0,'h20000,0,0,0,0,0);negatives=negatives+3;release_it();
  // All real ROM tiles, 16 distinct 8KiB working sets. Reuse logical slots
  // with different physical banks; run consecutive writes to stress RMW.
  for(bank=0;bank<16;bank=bank+1)begin
   for(tile=0;tile<512;tile=tile+1)
    for(lane=0;lane<16;lane=lane+1)begin
     put(tile*16+lane,'h200000+bank*8192+tile*16+lane,chr[bank*8192+tile*16+lane]);reads=reads+1;
    end
   lease();
   // A writer may keep running while owned; it cannot change the lease.
   put(0,'h210000,~chr[bank*8192]);@(negedge clk);sample=0;
   for(tile=0;tile<512;tile=tile+1)begin
    for(off=0;off<16;off=off+1)
     ask(tile,'h20000+bank*512+tile,off,0,1,chr[bank*8192+tile*16+(off%2)*8+off/2],'hffff);
    for(off=0;off<32;off=off+1)
     ask(tile,'h20000+bank*512+tile,off,1,1,off<16?chr[bank*8192+tile*16+(off%2)*8+off/2]:0,'hffff);
    ask(tile,'h20000+((bank+1)%16)*512+tile,0,0,0,0,0);negatives=negatives+1;
   end
   ask(0,'h20000+bank*512,16,0,0,0,'hffff);negatives=negatives+1;
   release_it();
  end
  // Bank change with only one byte: no stale plane or zero-plane success.
  put(0,'h200000,chr[0]);lease();ask(0,'h20000,0,0,0,0,1);
  ask(0,'h20000,16,1,0,0,1);ask(0,'h21e00,0,0,0,0,0);negatives=negatives+3;
  release_it();
  // Finish all but one byte; byte masks must not hide missing rows.
  for(lane=1;lane<15;lane=lane+1)put(lane,'h200000+lane,chr[lane]);
  lease();ask(0,'h20000,0,0,0,0,'h7fff);negatives=negatives+1;release_it();
  put(15,'h20000f,chr[15]);lease();ask(0,'h20000,15,0,1,chr[15],'hffff);
  // Releasing a pending query cancels its response.
  @(negedge clk);query=1;@(negedge clk);query=0;release_cache=1;
  @(negedge clk);if(response)$fatal(1,"response after cancellation");release_cache=0;negatives=negatives+1;
  // Reset during a partial write invalidates the complete prior working set.
  put(16,'h200010,chr[16]);@(negedge clk);reset=1;sample=0;
  repeat(2)@(negedge clk);reset=0;wait(initialized);lease();
  ask(0,'h20000,0,0,0,0,0);ask(1,'h20001,0,0,0,0,0);negatives=negatives+2;
  $display("PASS165 CHR tiles=8192 captured=%0d checks=%0d negatives=%0d",reads,checks,negatives);$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog");end
endmodule
