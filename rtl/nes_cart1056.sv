// SPDX-License-Identifier: MIT
// A fitted image has one cartridge wiring. Both the PPU and its lookahead
// translate through the same CHR registers. A pending mapper write affects
// the predicted address only; architectural state changes on M2.
module nes_cart1056 #(parameter integer MAPPER=3)(
 input wire clk, reset, ce, write_cpu, preview_write,
 input wire [15:0] cpu, input wire [7:0] data,
 input wire [13:0] ppu, lookahead,
 output wire [19:0] prg, output wire [17:0] chr, predicted_chr,
 output wire nt_page, irq
);
 generate if(MAPPER==21) begin: vrc4
   reg [4:0] bank0,bank1;
   reg swap;
   reg [1:0] mirror;
   reg [6:0] patterns[0:7];
   wire [3:0] page=cpu[15:12];
   wire a0=cpu[1]|cpu[6], a1=cpu[2]|cpu[7];
   wire write_chr=page>=11 && page<=14;
   wire [2:0] index={cpu[13:12]-2'd3,a1};
   wire [6:0] next_pattern=a0 ? {data[2:0],patterns[index][3:0]} :
                                 {patterns[index][6:4],data[3:0]};
   wire [6:0] predicted=(preview_write && write_chr && index==lookahead[12:10])
                       ? next_pattern : patterns[lookahead[12:10]];
   reg [7:0] reload_value,counter;
   reg [8:0] prescaler;
   reg enabled,after_ack,cycle_mode,pending;
   integer i;
   always @(posedge clk) begin
     if(reset) begin
       bank0<=0;bank1<=0;swap<=0;mirror<=0;
       for(i=0;i<8;i=i+1)patterns[i]<=0;
       enabled<=0;after_ack<=0;cycle_mode<=0;pending<=0;
       reload_value<=0;counter<=0;prescaler<=341;
     end else if(ce) begin
       if(enabled) begin
         prescaler<=prescaler<=3 ? prescaler+9'd338 : prescaler-9'd3;
         if(cycle_mode || prescaler<=3) begin
           if(&counter)begin counter<=reload_value;pending<=1;end
           else counter<=counter+1'b1;
         end
       end
       if(write_cpu)case(page)
         8: bank0<=data[4:0];
         9: if(a1)swap<=data[1];else mirror<=data[1:0];
         10: bank1<=data[4:0];
         11,12,13,14:patterns[index]<=next_pattern;
         15:case({a1,a0})
           0:reload_value[3:0]<=data[3:0];
           1:reload_value[7:4]<=data[3:0];
           2:begin after_ack<=data[0];enabled<=data[1];cycle_mode<=data[2];pending<=0;
             if(data[1])begin counter<=reload_value;prescaler<=341;end
           end
           3:begin enabled<=after_ack;pending<=0;end
         endcase
       endcase
     end
   end
   wire [4:0] bank=cpu[14:13]==3 ? 31 : cpu[14:13]==1 ? bank1 :
                   (cpu[14]^swap) ? 30 : bank0;
   assign prg={2'd0,bank,cpu[12:0]};
   assign chr={1'b0,patterns[ppu[12:10]],ppu[9:0]};
   assign predicted_chr={1'b0,predicted,lookahead[9:0]};
   assign nt_page=mirror[1] ? mirror[0] : mirror[0] ? ppu[11] : ppu[10];
   assign irq=pending;
 end else begin: discrete
   reg [4:0] latch;
   always @(posedge clk)
     if(reset) latch<=0;
     else if(ce && write_cpu && cpu[15])latch<=data[4:0];
   wire [1:0] next_bank=(preview_write && cpu[15]) ? data[1:0] : latch[1:0];
   assign prg={1'b0,(MAPPER==7 ? latch[3:0] : 4'd0),cpu[14:0]};
   assign chr={3'd0,(MAPPER==3 ? latch[1:0] : 2'd0),ppu[12:0]};
   assign predicted_chr={3'd0,(MAPPER==3 ? next_bank : 2'd0),lookahead[12:0]};
   assign nt_page=MAPPER==7 ? latch[4] : ppu[10];
   assign irq=1'b0;
 end endgenerate
endmodule
