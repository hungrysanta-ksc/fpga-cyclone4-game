// MCU byte window F1xxxx. Caller must keep core menu pause asserted.
// Registers 0000..016f: little-endian 64-bit word, commit on ordered byte 7.
// Palettes 0200..027f; HRAM 0300..037f; OAM 0400..049f;
// status/clear 0800; VRAM 4000..7fff; WRAM 8000..ffff.
module gbc_state_io(input wire clk,reset,paused,write_permitted,read_request,write_request,
 input wire[15:0]address,input wire[7:0]write_data,
 output wire busy,output reg done,output reg[7:0]read_data,output reg error,
 output wire[9:0]state_addr,output reg[63:0]state_data,
 output wire state_commit,input wire[63:0]state_read,
 output wire mem_active,output wire[1:0]mem_sel,output wire[14:0]mem_addr,
 output wire mem_write,input wire[7:0]mem_read);
 assign busy=phase!=0;
 reg[2:0]phase;reg[15:0]addr_q;reg[7:0]data_q;reg write_q,allowed_q,commit_q;
 reg[2:0]next_byte;reg[5:0]word_q;
 wire regs=addr_q<16'h0170;
 wire pal=addr_q[15:7]==9'h004;
 wire hram=addr_q[15:7]==9'h006;
 wire oam=addr_q[15:8]==8'h04&&addr_q[7:0]<160;
 wire mem=addr_q[15]||addr_q[14]||hram||oam;
 wire valid_address=regs||pal||mem;
 wire active=phase!=0&&allowed_q&&paused;
 assign state_addr=active?(pal?{3'b010,addr_q[6:0]}:regs?{4'b0,addr_q[8:3]}:10'h3ff):10'h3ff;
 assign state_commit=active&&commit_q&&(phase==2||phase==3);
 assign mem_active=active&&mem;
 assign mem_sel=addr_q[15]?2'd0:addr_q[14]?2'd1:oam?2'd2:2'd3;
 assign mem_addr=addr_q[14:0];
 assign mem_write=mem_active&&write_q&&phase==2;
 always @(posedge clk)begin
  done<=0;
  if(reset)begin phase<=0;addr_q<=0;data_q<=0;write_q<=0;allowed_q<=0;commit_q<=0;
   next_byte<=0;word_q<=0;state_data<=0;read_data<=0;error<=0;done<=0;
  end else begin
   if(!paused)next_byte<=0;
   if(read_request||write_request)begin
    if(phase!=0)error<=1;
    else begin phase<=1;addr_q<=address;data_q<=write_data;write_q<=write_request;allowed_q<=paused&&(!write_request||write_permitted);commit_q<=0;end
   end
   case(phase)
    1:begin
     phase<=2;
     if(addr_q==16'h0800)begin
      if(write_q)error<=0;
     end else if(!allowed_q||!paused||!valid_address)begin error<=1;allowed_q<=0;next_byte<=0;end
     else if(write_q)begin
      if(regs)begin
       if(addr_q[2:0]==0||(addr_q[2:0]==next_byte&&word_q==addr_q[8:3]))begin
        state_data[addr_q[2:0]*8+:8]<=data_q;word_q<=addr_q[8:3];next_byte<=addr_q[2:0]+1'b1;
        if(addr_q[2:0]==7)commit_q<=1;
       end else begin error<=1;next_byte<=0;end
      end else begin state_data[7:0]<=data_q;next_byte<=0;if(pal)commit_q<=1;end
     end
    end
    2:phase<=3;
    3:phase<=4;
    4:begin
     if(addr_q==16'h0800)read_data<={error,6'b0,paused};
     else if(!allowed_q||!paused||!valid_address)read_data<=8'hff;
     else if(mem)read_data<=mem_read;
     else if(pal)read_data<=state_read[7:0];
     else read_data<=state_read[addr_q[2:0]*8+:8];
     done<=1;phase<=0;commit_q<=0;
    end
   endcase
  end
 end
endmodule
