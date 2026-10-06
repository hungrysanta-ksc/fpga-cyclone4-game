// SPDX-License-Identifier: MIT
// Original031 integrated transport. No board PLL, loader, producer or pad assignment.
module nes_transport(
 input wire queue_clk,host_clk,reset,
 input wire [15:0] reset_epoch,
 input wire [1:0] p_op,
 input wire [15:0] p_epoch,p_seq,
 input wire [11:0] p_length,
 input wire [7:0] p_data,
 output wire p_accept,
 output wire [3:0] p_error,
 input wire [23:0] snes_addr,
 input wire read_n,write_n,romsel_n,
 input wire [7:0] snes_data_in,
 output wire [7:0] bus_data,
 output wire databus_oe_n,databus_dir,
 output wire ready,busy,fault,host_read_owned,
 output wire [3:0] bus_error,frontend_error
);
 wire cmd_valid,cmd_ready,rsp_valid,rsp_ready,rsp_accept,rsp_data_valid;
 wire [1:0] cmd_op;
 wire [15:0] cmd_epoch,cmd_seq,rsp_epoch,rsp_seq;
 wire [11:0] cmd_address,rsp_length;
 wire [3:0] rsp_error;
 wire [7:0] rsp_data;
 wire reg_write,reg_read,data_read;
 wire [3:0] reg_address;
 wire [7:0] reg_wdata,reg_rdata,data;
 wire reg_rvalid,data_valid;
 nes_packet_cdc_ram bridge(.*);
 nes_host_stage stage(.*);
 nes_snes_frontend frontend(.*);
endmodule
