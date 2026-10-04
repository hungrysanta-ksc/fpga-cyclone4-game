// 8192-sample stereo delay client for the independent 16-bit PSRAM port.
// BASE_WORD is a PSRAM request-word address; physical byte addresses are twice
// this value. Each sample stores left then right in two adjacent words.
module audio_psram_delay_client #(
 parameter [22:0] BASE_WORD = 23'h300000,
 parameter integer INDEX_BITS = 13
)(
 input wire clk,input wire reset,
 input wire sample_valid,input wire signed [15:0]sample_l,sample_r,
 input wire[INDEX_BITS-1:0]delay_samples,
 output wire sample_ready,output reg busy,
 output reg delayed_valid,output reg signed[15:0]delayed_l,delayed_r,
 output reg req_valid,output reg req_write,output reg[22:0]req_addr,
 output reg[15:0]req_wdata,input wire req_ready,
 input wire rsp_valid,input wire[15:0]rsp_rdata,
 output reg protocol_error,output reg sample_overrun
);
 localparam[1:0]IDLE=0,ISSUE=1,WAIT_RSP=2;
 reg[1:0]state;
 reg[2:0]op_index;
 reg need_read;
 reg[INDEX_BITS-1:0]write_index,read_index;
 reg[INDEX_BITS:0]fill_count;
 reg[15:0]write_l,write_r,read_l,read_r;
 wire read_op=need_read&&op_index<2;
 wire word_side=read_op?op_index[0]:(op_index-(need_read?2:0));
 wire[INDEX_BITS:0]word_index={read_op?read_index:write_index,1'b0}+word_side;
 wire last_op=op_index==(need_read?3:1);
 assign sample_ready=!busy&&!reset&&!protocol_error;
 always @*begin
  req_valid=state==ISSUE&&!protocol_error;
  req_write=!read_op;
  req_addr=BASE_WORD+word_index;
  req_wdata=word_side?write_r:write_l;
 end
 always @(posedge clk)begin
  delayed_valid<=0;
  if(reset)begin
   state<=IDLE;busy<=0;op_index<=0;need_read<=0;write_index<=0;read_index<=0;fill_count<=0;
   write_l<=0;write_r<=0;read_l<=0;read_r<=0;delayed_l<=0;delayed_r<=0;
   protocol_error<=0;sample_overrun<=0;
  end else begin
   if(sample_valid&&busy)sample_overrun<=1;
   case(state)
    IDLE:if(sample_valid)begin
     if(delay_samples==0)protocol_error<=1;
     else begin
      busy<=1;op_index<=0;write_l<=sample_l;write_r<=sample_r;read_l<=0;read_r<=0;
      need_read<=fill_count>=delay_samples;read_index<=write_index-delay_samples;state<=ISSUE;
     end
    end
    ISSUE:if(req_ready)state<=WAIT_RSP;
    WAIT_RSP:if(rsp_valid)begin
     if(read_op)begin if(word_side)read_r<=rsp_rdata;else read_l<=rsp_rdata;end
     if(last_op)begin
      state<=IDLE;busy<=0;write_index<=write_index+1'b1;
      if(fill_count!={1'b1,{INDEX_BITS{1'b0}}})fill_count<=fill_count+1'b1;
      delayed_valid<=1;
      if(need_read)begin delayed_l<=read_l;delayed_r<=read_r;end
      else begin delayed_l<=0;delayed_r<=0;end
     end else begin op_index<=op_index+1'b1;state<=ISSUE;end
    end
    default:begin state<=IDLE;busy<=0;protocol_error<=1;end
   endcase
  end
 end
endmodule
