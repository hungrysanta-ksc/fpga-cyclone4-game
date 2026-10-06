// SPDX-License-Identifier: MIT
//031 RAM-inference variant of027; ownership/protocol unchanged. Original027 is preserved.
module nes_packet_queue_ram #(parameter integer SLOT_BYTES=3072)(
 input wire clk,reset,
 input wire [15:0] reset_epoch,
 input wire [1:0] p_op,
 input wire [15:0] p_epoch,p_seq,
 input wire [11:0] p_length,
 input wire [7:0] p_data,
 output reg p_accept,
 output reg [3:0] p_error,
 input wire [1:0] c_op,
 input wire [15:0] c_epoch,c_seq,
 input wire [11:0] c_address,
 output reg c_accept,c_data_valid,
 output wire [7:0] c_data,
 output reg [3:0] c_error,
 output wire packet_ready,consumer_active,
 output wire [11:0] ready_length,
 output wire [15:0] ready_sequence,epoch,
 output wire [3:0] slot_states
);
 // Producer: 1 begin, 2 sequential byte write, 3 publish.
 // Consumer: 1 acquire, 2 sequential byte read, 3 commit. Zero is idle.
 localparam [1:0] FREE=0,WRITING=1,READY=2,READING=3;
 reg [1:0] state[0:1];
 (* ramstyle="M9K" *) reg [7:0] memory[0:2*SLOT_BYTES-1];
 reg [7:0] ram_q;
 reg [11:0] length_q[0:1],written[0:1],read_count[0:1];
 reg [15:0] sequence_q[0:1],epoch_q,next_p,next_c;
 reg wp,rp;
 assign packet_ready=!reset && state[rp]==READY;
 assign consumer_active=!reset && state[rp]==READING;
 assign ready_length=packet_ready ? length_q[rp] : 12'd0;
 assign ready_sequence=packet_ready ? sequence_q[rp] : 16'd0;
 assign epoch=epoch_q;
 assign slot_states={state[1],state[0]};
 // Separate synchronous RAM port registers; no output reset/default-zero mux inside the RAM template.
 wire ram_we=!reset && p_op==2 && p_epoch==epoch_q && p_seq!=0 && p_seq==next_p &&
   state[wp]==WRITING && written[wp]<length_q[wp];
 wire ram_re=!reset && c_op==2 && c_epoch==epoch_q && c_seq!=0 && c_seq==next_c &&
   state[rp]==READING && c_address==read_count[rp] && c_address<length_q[rp];
 wire [12:0] ram_wa=(wp ? SLOT_BYTES : 0)+written[wp];
 wire [12:0] ram_ra=(rp ? SLOT_BYTES : 0)+c_address;
 always @(posedge clk) begin
  if(ram_we)memory[ram_wa]<=p_data;
  if(ram_re)ram_q<=memory[ram_ra];
 end
 assign c_data=c_data_valid ? ram_q : 8'd0;
 integer k;
 always @(posedge clk) begin
  p_accept<=0;p_error<=0;c_accept<=0;c_error<=0;c_data_valid<=0;
  if(reset) begin
   epoch_q<=reset_epoch;next_p<=1;next_c<=1;wp<=0;rp<=0;
   for(k=0;k<2;k=k+1) begin
    state[k]<=FREE;length_q[k]<=0;written[k]<=0;read_count[k]<=0;sequence_q[k]<=0;
   end
  end else begin
   if(p_op!=0) begin
    if(p_epoch!=epoch_q) p_error<=3;
    else if(p_seq==0 || p_seq!=next_p) p_error<=4;
    else case(p_op)
     1: if(state[wp]!=FREE) p_error<=1;
        else if(p_length==0 || p_length>SLOT_BYTES) p_error<=2;
        else begin
         state[wp]<=WRITING;length_q[wp]<=p_length;sequence_q[wp]<=p_seq;
         written[wp]<=0;read_count[wp]<=0;p_accept<=1;
        end
     2: if(state[wp]!=WRITING) p_error<=1;
        else if(written[wp]>=length_q[wp]) p_error<=6;
        else begin written[wp]<=written[wp]+1'b1;p_accept<=1;end
     3: if(state[wp]!=WRITING) p_error<=1;
        else if(written[wp]!=length_q[wp]) p_error<=5;
        else begin state[wp]<=READY;wp<=~wp;next_p<=next_p+1'b1;p_accept<=1;end
    endcase
   end
   if(c_op!=0) begin
    if(c_epoch!=epoch_q) c_error<=3;
    else if(c_seq==0 || c_seq!=next_c) c_error<=4;
    else case(c_op)
     1: if(state[rp]==READY) begin state[rp]<=READING;c_accept<=1;end
        // Not yet published: wait without permitting a read.
     2: if(state[rp]!=READING) c_error<=7;
        else if(c_address!=read_count[rp] || c_address>=length_q[rp]) c_error<=8;
        else begin
         c_data_valid<=1;c_accept<=1;
         read_count[rp]<=read_count[rp]+1'b1;
        end
     3: if(state[rp]!=READING) c_error<=7;
        else if(read_count[rp]!=length_q[rp]) c_error<=5;
        else begin state[rp]<=FREE;rp<=~rp;next_c<=next_c+1'b1;c_accept<=1;end
    endcase
   end
  end
 end
endmodule
