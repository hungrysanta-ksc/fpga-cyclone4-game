// C19 boot-only fixed 512-byte duplex word queues. SPI framing is external.
// Read a fully written previous block while accepting the next block.
module gbc_load_words(
 input wire clk,reset,start,input wire do_write,do_read,
 input wire[22:0]write_base,read_base,input wire rx_valid,input wire[15:0]rx_data,
 input wire tx_take,output wire tx_valid,output wire[15:0]tx_data,
 output wire primed,done,output reg error,
 output wire req_valid,req_write,input wire req_ready,
 output wire[22:0]req_addr,output wire[15:0]req_data,
 input wire rsp_valid,input wire[15:0]rsp_data
);
 (* ramstyle="logic" *)reg[15:0]wf[0:3],rf[0:3];
 reg[1:0]wi,wo,ri,ro;reg[2:0]wc,rc;
 reg[8:0]n,received,sent,wissued,rissued,wcompleted;
 reg[22:0]wb,rb;reg writing,reading,active,busy,pending_write;
 wire choose_read=reading&&(rissued<n)&&(rc<4)&&((rc<2)||(wc==0));
 wire choose_write=writing&&(wc!=0)&&!choose_read;
 assign req_valid=active&&!error&&!busy&&(choose_read||choose_write);
 assign req_write=choose_write;
 assign req_addr=choose_write?wb+wissued:rb+rissued;
 assign req_data=wf[wo];
 wire accept=req_valid&&req_ready;
 wire wpop=accept&&req_write;
 wire rpush=rsp_valid&&busy&&!pending_write;
 wire wpush=active&&writing&&rx_valid;
 wire rpop=active&&reading&&tx_take;
 assign tx_data=rf[ro];assign tx_valid=rc!=0;
 assign primed=active&&(!reading||rc>=(n<2?n:2));
 assign done=active&&!error&&!busy&&(!writing||(received==n&&wcompleted==n))&&(!reading||sent==n);
 always @(posedge clk)begin
  if(reset)begin wi<=0;wo<=0;ri<=0;ro<=0;wc<=0;rc<=0;n<=0;received<=0;sent<=0;
   wissued<=0;rissued<=0;wcompleted<=0;wb<=0;rb<=0;writing<=0;reading<=0;active<=0;busy<=0;pending_write<=0;error<=0;
  end else if(start)begin
   wi<=0;wo<=0;ri<=0;ro<=0;wc<=0;rc<=0;n<=256;received<=0;sent<=0;
   wissued<=0;rissued<=0;wcompleted<=0;wb<=write_base;rb<=read_base;
   writing<=do_write;reading<=do_read;active<=1;busy<=0;pending_write<=0;error<=0;
  end else begin
   if(wpush)begin
    if(received>=n||(wc==4&&!wpop))error<=1;
    else begin wf[wi]<=rx_data;wi<=wi+1'b1;received<=received+1'b1;end
   end
   if(wpop)wo<=wo+1'b1;
   case({wpush,wpop})2'b10:wc<=wc+1'b1;2'b01:wc<=wc-1'b1;default:;endcase
   if(rpush)begin if(rc==4&&!rpop)error<=1;rf[ri]<=rsp_data;ri<=ri+1'b1;end
   if(rpop)begin if(rc==0||sent>=n)error<=1;else begin ro<=ro+1'b1;sent<=sent+1'b1;end end
   case({rpush,rpop})2'b10:rc<=rc+1'b1;2'b01:rc<=rc-1'b1;default:;endcase
   if(accept)begin busy<=1;pending_write<=req_write;if(req_write)wissued<=wissued+1'b1;else rissued<=rissued+1'b1;end
   if(rsp_valid&&busy)begin busy<=0;if(pending_write)wcompleted<=wcompleted+1'b1;end
  end
 end
endmodule
