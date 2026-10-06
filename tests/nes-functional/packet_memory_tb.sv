// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module packet_memory_tb;
 reg queue_clk=0,host_clk=0,reset=1;
 real qhalf=23.280423,hhalf=5.952381,hphase=1.1;integer unused;
 initial begin unused=$value$plusargs("QHALF=%f",qhalf);forever #(qhalf)queue_clk=~queue_clk;end
 initial begin unused=$value$plusargs("HHALF=%f",hhalf);unused=$value$plusargs("HPHASE=%f",hphase);#(hphase);forever #(hhalf)host_clk=~host_clk;end
 reg [15:0] reset_epoch=7,desc_epoch=7,desc_seq=1;
 reg desc_valid=0;wire desc_ready;reg [23:0] desc_base=0;reg [11:0] desc_length=0;
 wire mem_req_valid,mem_req_ready,mem_rsp_valid,mem_rsp_ready,mem_rsp_error;
 wire [23:0] mem_req_address,mem_rsp_address;wire [15:0] mem_req_epoch,mem_rsp_epoch;wire [7:0] mem_rsp_data;
 wire [1:0] p_op;wire [15:0] p_epoch,p_seq;wire [11:0] p_length;wire [7:0] p_data;
 wire p_accept,done,producer_fault,exhausted;wire [3:0] p_error;wire [7:0] producer_error;wire [15:0] published;
 wire ready,busy,fault,host_read_owned;wire [3:0] bus_error,frontend_error;wire [127:0] frontend_snapshot;
 reg [23:0] snes_addr=0;reg read_n=1,write_n=1,romsel_n=1;reg [7:0] snes_data_in=0;
 wire [7:0] bus_data;wire databus_oe_n,databus_dir;
 nes_packet_memory_producer #(.TIMEOUT_CYCLES(32)) producer(.*);
 nes_transport transport(.*);
 reg [7:0] memory[0:16383];integer mode=0,cycles=0,requests=0,writes=0,publications=0,checks=0,bytes_read=0,acquire_retries=0,fd;
 reg pending=0,rvalid=0,rerror=0;integer delay_count=0;
 reg [23:0] saved_addr=0,raddress=0;reg [15:0] saved_epoch=0,repoch=0;reg [7:0] rdata=0;
 reg inject=0;reg [15:0] injected_epoch=0;
 assign mem_req_ready=!reset && mode!=1 && !pending && !rvalid && cycles%5!=0;
 assign mem_rsp_valid=inject || rvalid;
 assign mem_rsp_epoch=inject ? injected_epoch : repoch;
 assign mem_rsp_address=inject ? mem_req_address : raddress;
 assign mem_rsp_data=inject ? 8'hde : rdata;
 assign mem_rsp_error=inject ? 1'b0 : rerror;
 always @(posedge queue_clk)begin
  cycles<=cycles+1;rvalid<=0;
  if(reset)begin pending<=0;end
  else begin
   if(mem_req_valid && mem_req_ready)begin
    if(pending)$fatal(1,"more than one outstanding request");
    saved_addr<=mem_req_address;saved_epoch<=mem_req_epoch;pending<=1;
    delay_count<=1+(mem_req_address%7);requests++;
    $fdisplay(fd,"R %0t %0d %0d %0d",$time,mem_req_epoch,p_seq,mem_req_address);
   end
   if(pending && mode!=2)begin
    if(delay_count!=0)delay_count<=delay_count-1;
    else begin
     pending<=0;rvalid<=1;repoch<=saved_epoch;raddress<=saved_addr+(mode==3?1:0);
     rdata<=memory[saved_addr%16384];rerror<=mode==4 || (mode==6 && saved_addr==5);
    end
   end
   if(desc_valid && desc_ready)$fdisplay(fd,"D %0t %0d %0d %0d %0d",$time,desc_epoch,desc_seq,desc_base,desc_length);
   if(done)$fdisplay(fd,"P %0t %0d %0d",$time,p_epoch,published);
   if(p_op==2)writes++;
   if(p_op==3)publications++;
  end
 end
 task automatic pass(input string name);checks++;$display("PASS CASE %s",name);endtask
 task automatic restart;
  @(negedge queue_clk);reset=1;reset_epoch=reset_epoch+1'b1;desc_valid=0;inject=0;
  read_n=1;write_n=1;romsel_n=1;mode=0;
  #0.001;if(mem_req_valid || p_op!=0 || desc_ready || mem_rsp_ready)$fatal(1,"reset output gating");
  repeat(6)@(negedge queue_clk);reset=0;repeat(12)@(negedge queue_clk);
 endtask
 task automatic descriptor(input integer base_addr,input integer length,input integer seqnum,input integer epoch_offset=0);
  while(!desc_ready)@(negedge queue_clk);
  desc_base=base_addr;desc_length=length;desc_seq=seqnum;desc_epoch=reset_epoch+epoch_offset;desc_valid=1;
  @(negedge queue_clk);desc_valid=0;
 endtask
 task automatic wr(input integer a,input integer value);
  snes_addr=a;snes_data_in=value;romsel_n=1;#20;write_n=0;#180;write_n=1;#20;snes_addr=24'h123456;#100;
 endtask
 task automatic rd(input integer a,input integer want,input integer payload);
  snes_addr=a;romsel_n=payload?0:1;#20;read_n=0;#160;
  if(databus_oe_n || !databus_dir || bus_data!==want[7:0])$fatal(1,"read address%h got%h wanted%h frontend%h",a,bus_data,want,frontend_error);
  if(payload)begin bytes_read++;$fdisplay(fd,"B %0t %0d %0d",$time,a,bus_data);end
  #60;read_n=1;romsel_n=1;snes_addr=24'habcd00;
  #0.001;if(!databus_oe_n || databus_dir)$fatal(1,"raw release");#100;
 endtask
 task automatic consume(input integer seqnum,input integer base_addr,input integer length);
  integer n;
  wr(24'h6002,reset_epoch&255);wr(24'h6003,reset_epoch>>8);wr(24'h6004,seqnum&255);wr(24'h6005,seqnum>>8);wr(24'h6000,1);
  n=0;while(!ready && !fault && n<50000)begin #100;n++;if(!busy && !ready && !fault)begin acquire_retries++;wr(24'h6000,1);end end
  if(!ready || fault || producer_fault)$fatal(1,"acquire failed producer%h bus%h",producer_error,bus_error);
  rd(24'h6006,length&255,0);rd(24'h6007,length>>8,0);
  for(integer i=0;i<length;i++)rd(24'h408000+i,memory[(base_addr+i)%16384],1);
  rd(24'h6008,length&255,0);rd(24'h6009,length>>8,0);
  wr(24'h6000,2);n=0;while(busy && n<50000)begin #100;n++;end
  if(busy || fault || host_read_owned || frontend_error)$fatal(1,"commit");
 endtask
 task automatic failure(input integer code,input string name);
  integer n;n=0;while(!producer_fault && n<300)begin @(negedge queue_clk);n++;end
  if(!producer_fault || producer_error!=code || published!=0 || ready)$fatal(1,"fault mismatch wanted%h got%h published%0d",code,producer_error,published);
  repeat(10)@(negedge queue_clk);
  if(mem_req_valid || p_op!=0 || desc_ready)$fatal(1,"fault did not stop");pass(name);
 endtask
 integer saved_requests,saved_writes,saved_publications;
 initial begin
  fd=$fopen("memory-trace.tsv","w");$readmemh("packets.hex",memory);restart();
  fork
   begin
    for(integer i=0;i<8;i++)descriptor(i*2008,2008,i+1);
   end
   begin
    while(published!=2)@(negedge queue_clk);
    saved_requests=requests;repeat(300)@(negedge queue_clk);
    if(published!=2 || producer_fault || requests!=saved_requests || requests!=4016)$fatal(1,"full queue lost ownership or requested bytes");
    pass("two_slots_full_no_memory_request_no_drop");
    for(integer i=0;i<8;i++)consume(i+1,i*2008,2008);
   end
  join
  if(published!=8 || bytes_read!=16064 || requests!=16064 || writes!=16064 || publications!=8)$fatal(1,"eight packet accounting");
  pass("eight_reference_packets_exact_via_044_bus");
  restart();saved_requests=requests;descriptor(0,0,1);failure(1,"zero_length_rejected");if(requests!=saved_requests)$fatal;
  restart();descriptor(0,3073,1);failure(1,"oversized_length_rejected");
  restart();descriptor(0,1,1,-1);failure(2,"stale_descriptor_rejected");
  restart();descriptor(0,1,2);failure(3,"out_of_order_sequence_rejected");
  restart();descriptor(24'hffffff,2,1);failure(4,"address_wrap_rejected");
  restart();mode=1;descriptor(0,1,1);failure('h11,"request_timeout");
  restart();mode=2;descriptor(0,1,1);failure('h12,"response_timeout_no_publish");
  restart();mode=3;descriptor(0,1,1);failure('h13,"wrong_response_address");
  restart();mode=4;descriptor(0,1,1);failure('h14,"memory_service_error");
  restart();saved_writes=writes;saved_publications=publications;mode=6;descriptor(0,8,1);
  failure('h14,"partial_memory_error_not_published");
  if(writes-saved_writes!=5 || publications!=saved_publications)$fatal(1,"partial failure published");
  restart();injected_epoch=reset_epoch;inject=1;@(negedge queue_clk);inject=0;failure('h15,"unsolicited_response");
  restart();mode=2;descriptor(0,8,1);while(!pending)@(negedge queue_clk);
  injected_epoch=reset_epoch;restart(); // outstanding old epoch cancelled by common reset
  inject=1;@(negedge queue_clk);inject=0;
  descriptor(2008,8,1);consume(1,2008,8);
  if(producer_fault || published!=1)$fatal(1,"old response polluted new epoch");pass("RESET_old_response_drained_new_packet_exact");
  restart();mode=2;descriptor(0,8,1);while(!pending)@(negedge queue_clk);
  injected_epoch=reset_epoch-1;inject=1;@(negedge queue_clk);inject=0;mode=0;
  consume(1,0,8);if(producer_fault)$fatal(1,"stale response while waiting");pass("stale_response_does_not_complete_current_read");
  restart();fork descriptor(0,3072,1);consume(1,0,3072);join
  if(published!=1 || producer_fault)$fatal;pass("maximum3072_packet");
  restart();fork descriptor(24'hffffff,1,1);consume(1,24'hffffff,1);join
  pass("last_address_one_byte_boundary");
  if(acquire_retries==0)$fatal(1,"empty acquire retry untested");
  $display("ACQUIRE retries=%0d",acquire_retries);
  $display("PASS MEMORY PRODUCER checks=%0d bytes=%0d",checks,bytes_read);$fclose(fd);$finish;
 end
 initial begin #100000000;$fatal(1,"test watchdog");end
endmodule
