// SPDX-License-Identifier: MIT
// Local NES bus and paused checkpoint access share the same physical RAMs.
// The controller holds paused until its complete restore has been verified.
module nes_checkpoint_memory #(parameter CHR_RAM=1, DEVICE_CHR=0) (
 input wire clk, reset, paused,
 input wire [24:0] cpumem_addr, input wire cpumem_write, input wire [7:0] cpumem_dout,
 input wire [21:0] ppumem_addr, input wire ppumem_write, input wire [7:0] ppumem_dout,
 input wire [7:0] external_cpu_data, external_ppu_data,
 input wire [12:0] chr_scan_address, output wire [7:0] chr_scan_data, output wire chr_changed,
 input wire [10:0] native_nt_address, output wire [7:0] native_nt_data, output wire native_nt_write,
 output wire [7:0] cpumem_din, ppumem_din, output reg init_done,
 input wire [24:0] state_address, input wire state_read,state_write,input wire [7:0] state_wdata,
 output wire state_accepted, output reg state_rvalid,output wire [7:0] state_rdata
);
 localparam CPU=0, NT=1, PRG=2, CHR=3;
 reg [12:0] scrub;
 wire clear_mem=!reset && !init_done;
 wire [3:0] state_sel={
   CHR_RAM!=0 && state_address[24:13]==12'h100,
   state_address[24:13]==12'h1e0,
   state_address[24:11]==14'h740,
   state_address[24:11]==14'h700};
 assign state_accepted=paused && init_done && !reset && (state_read ^ state_write) && |state_sel;
 reg [3:0] read_sel;
 reg [7:0] held_read;
 wire [7:0] selected_q;
 wire [7:0] q[0:3];
 always @(posedge clk or posedge reset) begin
   if(reset) begin scrub<=0; init_done<=0; state_rvalid<=0; read_sel<=0; held_read<=0; end
   else begin
     if(clear_mem) begin
       if(&scrub) init_done<=1;
       else scrub<=scrub+1'b1;
     end
     state_rvalid<=state_accepted && state_read;
     if(state_rvalid) held_read<=selected_q;
     if(state_accepted && state_read) read_sel<=state_sel;
   end
 end
 wire [3:0] live_sel={
    CHR_RAM!=0 && ppumem_addr[21:13]==9'h100, cpumem_addr[24:13]==12'h1e0,
    ppumem_addr[21:11]==11'h740, cpumem_addr[24:11]==14'h700};
 wire [3:0] live_write={ppumem_write,cpumem_write,ppumem_write,cpumem_write};
 // While the core is paused only the selected state bank is observable.
 // The inactive port of each CPU/PPU pair can follow the same address.
 wire service_cycle=clear_mem || state_accepted;
 wire [12:0] service_address=clear_mem ? scrub : state_address[12:0];
 wire [7:0] service_data=clear_mem ? 8'd0 : state_wdata;
 wire [12:0] cpu_address=service_cycle ? service_address : cpumem_addr[12:0];
 wire [12:0] ppu_address=service_cycle ? service_address : ppumem_addr[12:0];
 wire [7:0] cpu_data=service_cycle ? service_data : cpumem_dout;
 wire [7:0] ppu_data=service_cycle ? service_data : ppumem_dout;
 genvar i;
 generate for(i=0;i<4;i=i+1) begin: region
   localparam WIDTH=(i==CPU || i==NT)?11:13;
   wire ppu=(i==NT || i==CHR);
   wire service=state_accepted && state_sel[i];
   wire [WIDTH-1:0] addr=ppu ? ppu_address[WIDTH-1:0] : cpu_address[WIDTH-1:0];
   wire [7:0] value=ppu ? ppu_data : cpu_data;
   wire wr=(clear_mem && (WIDTH==13 || scrub<2048)) || (service && state_write) ||
           (!reset && init_done && !paused && live_sel[i] && live_write[i]);
   if(i==NT) begin: nametable
     assign native_nt_write=wr;
     nes_native_ciram165 ram(clk,wr,addr,value,q[i],native_nt_address,native_nt_data);
   end else if(i==CHR && CHR_RAM!=0 && DEVICE_CHR!=0) begin: fitted_pattern
     altsyncram #(.operation_mode("BIDIR_DUAL_PORT"),.intended_device_family("Cyclone IV E"),
       .ram_block_type("M9K"),.width_a(8),.width_b(8),.widthad_a(13),.widthad_b(13),
       .numwords_a(8192),.numwords_b(8192),.width_byteena_a(1),.width_byteena_b(1),
       .address_reg_b("CLOCK1"),.outdata_reg_a("UNREGISTERED"),.outdata_reg_b("UNREGISTERED"),
       .read_during_write_mode_mixed_ports("DONT_CARE"),
       .read_during_write_mode_port_a("NEW_DATA_NO_NBE_READ")) ram(
       .clock0(clk),.clock1(clk),.clocken0(1'b1),.clocken1(1'b1),.clocken2(1'b1),.clocken3(1'b1),
       .address_a(addr),.address_b(chr_scan_address),.data_a(value),.data_b(8'd0),
       .byteena_a(1'b1),.byteena_b(1'b1),.wren_a(wr),.wren_b(1'b0),.rden_a(1'b1),.rden_b(1'b1),
       .aclr0(1'b0),.aclr1(1'b0),.addressstall_a(1'b0),.addressstall_b(1'b0),
       .q_a(q[i]),.q_b(chr_scan_data),.eccstatus());
     assign chr_changed=wr;
   end else if(i==CHR && CHR_RAM!=0) begin: pattern
     (* ramstyle="M9K" *) reg [7:0] mem[0:8191];
     reg [7:0] live_q,scan_q;
     always @(posedge clk) begin
       if(wr) mem[addr]<=value;
       live_q<=mem[addr];
       scan_q<=mem[chr_scan_address];
     end
     assign q[i]=live_q;
     assign chr_scan_data=scan_q;
     assign chr_changed=wr;
   end else if(i!=CHR) begin: local_ram
     nes_local_memory_ram #(.AW(WIDTH)) ram(clk,wr,addr,value,q[i]);
   end else begin
     assign q[i]=0;
     assign chr_changed=0;
     assign chr_scan_data=0;
   end
 end endgenerate
 assign selected_q=({8{read_sel[CPU]}} & q[CPU]) | ({8{read_sel[NT]}} & q[NT]) |
                   ({8{read_sel[PRG]}} & q[PRG]) | ({8{read_sel[CHR]}} & q[CHR]);
 assign state_rdata=paused && !reset ? (state_rvalid ? selected_q : held_read) : 0;
 assign cpumem_din=!init_done || reset?0:live_sel[CPU]?q[CPU]:live_sel[PRG]?q[PRG]:external_cpu_data;
 assign ppumem_din=!init_done || reset?0:live_sel[NT]?q[NT]:live_sel[CHR]?q[CHR]:external_ppu_data;
endmodule

