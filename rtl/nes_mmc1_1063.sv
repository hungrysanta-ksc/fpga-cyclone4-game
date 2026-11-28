// MMC1B, 256 KiB PRG ROM, 8 KiB CHR RAM and one 8 KiB battery RAM.
module nes_mmc1_1063(
 input wire clk, reset, cpu_ce, cpu_write, preview_write,
 input wire [15:0] cpu_address, input wire [7:0] cpu_data,
 input wire [13:0] ppu_address, lookahead,
 input wire restore, input wire [25:0] restored_state,
 output wire [25:0] saved_state,
 output wire [17:0] prg_address, output wire [12:0] chr_address, predicted_chr,
 output wire nt_page, ram_selected
);
 reg [4:0] control, chr0, chr1, prg, shift;
 reg last_write;
 wire reg_write = cpu_address[15] && cpu_write;
 wire accept_bit = !last_write && !cpu_data[7];
 wire [4:0] shifted = {cpu_data[0],shift[4:1]};
 wire [1:0] dest = cpu_address[14:13];
 assign saved_state = {last_write, shift, prg, chr1, chr0, control};

 always @(posedge clk) begin
   if(reset) begin
     control<=5'h0c; chr0<=0; chr1<=0; prg<=0; shift<=5'h10; last_write<=0;
   end else if(restore) begin
     {last_write,shift,prg,chr1,chr0,control}<=restored_state;
   end else if(cpu_ce) begin
     last_write<=reg_write;
     if(reg_write) begin
       if(cpu_data[7]) begin shift<=5'h10; control<=control | 5'h0c; end
       else if(accept_bit) begin
         if(shift[0]) begin
           case(dest)
             0: control<=shifted;
             1: chr0<=shifted;
             2: chr1<=shifted;
             3: prg<=shifted;
           endcase
           shift<=5'h10;
         end else shift<=shifted;
       end
     end
   end
 end

 wire [3:0] prg_bank = !control[3] ? {prg[3:1],cpu_address[14]} :
                       (control[2]==cpu_address[14]) ? (control[2]?4'hf:4'h0) : prg[3:0];
 assign prg_address = {prg_bank,cpu_address[13:0]};
 assign ram_selected = cpu_address[15:13]==3'b011 && !prg[4];
 assign nt_page = control[1] ? (control[0]?ppu_address[11]:ppu_address[10]) : control[0];
 assign chr_address = {control[4] ? (ppu_address[12]?chr1[0]:chr0[0]) : ppu_address[12],ppu_address[11:0]};

 // Lookahead may coincide with the fifth serial write, before registers latch.
 wire commit_preview = preview_write && cpu_address[15] && accept_bit && shift[0];
 wire new_mode = commit_preview && dest==0 ? shifted[4] : control[4];
 wire select_chr1 = lookahead[12];
 wire chr_bit = commit_preview && dest==(select_chr1?2'd2:2'd1) ? shifted[0] :
                (select_chr1 ? chr1[0] : chr0[0]);
 assign predicted_chr = {new_mode ? chr_bit : select_chr1,lookahead[11:0]};
endmodule
