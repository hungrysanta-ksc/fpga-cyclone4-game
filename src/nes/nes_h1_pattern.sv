// SPDX-License-Identifier: MIT
// H1 diagnostic integration; board clock/pads/loader remain external.
module nes_h1_pattern(
 input wire queue_clk,host_clk,reset,
 input wire [15:0] reset_epoch,
 input wire [23:0] snes_addr,
 input wire read_n,write_n,romsel_n,
 input wire [7:0] snes_data_in,
 output wire [7:0] bus_data,
 output wire databus_oe_n,databus_dir,
 output wire ready,busy,fault,host_read_owned,
 output wire [3:0] bus_error,frontend_error,
 output wire producer_fault,exhausted,
 output wire [3:0] producer_error,
 output wire [15:0] published
);
 wire [1:0] p_op;
 wire [15:0] p_epoch,p_seq;
 wire [11:0] p_length;
 wire [7:0] p_data;
 wire p_accept;
 wire [3:0] p_error;
 nes_h1_pattern_producer producer(.*);
 nes_transport transport(.*);
endmodule
