# SPDX-License-Identifier: MIT
"""Materialize native lease/fill -> host-clock records and prepared/commit link.

The host ports are logical ready/valid, not an implemented SPI/MMIO endpoint.
"""
import shutil
from nes_game147 import ROOT
from nes_native_memory165 import prepare as memory_prepare,FILES as MEMORY_FILES,PORTS as FILL_PORTS
from nes_native_frame165 import PORTS as FRAME_PORTS

FILES=MEMORY_FILES+['nes_native_export165.sv','nes_native_mailbox165.sv']
PORTS='''output wire native_host_valid,input wire native_host_ready,output wire [95:0] native_host_data,
input wire native_host_ack_valid,native_host_ack_accept,input wire [15:0] native_host_ack_generation,
output wire native_host_ack_ready,
'''
BINDING='''
wire native_tx_valid,native_tx_ready,native_ack_valid,native_ack_ready;wire [95:0] native_tx_data;
wire [16:0] native_ack_data;wire [3:0] native_export_error;
nes_native_export165 native_export(
 .clk(clk),.reset(reset),.enable(1'b1),
 .frame_owned(native_frame_owned),.geometry_valid(native_geometry_valid&&!rom_fault&&!native_arbiter_fault),.frame_generation(native_generation),
 .row_count(native_row_count),.group_count(native_group_count),.object_count(native_object_count),.exception_count(native_exception_count),.palette_count(native_palette_count),
 .release_frame(native_release_frame),.query(native_query),.query_kind(native_query_kind),.query_index(native_query_index),.query_generation(native_query_generation),
 .response(native_response),.hit(native_hit),.data(native_data),.fill_start(native_fill_start),.fill_busy(native_fill_busy),.fill_done(native_fill_done),.fill_success(native_fill_success),
 .byte_valid(native_byte_valid),.byte_ready(native_byte_ready),.byte_data(native_byte_data),.byte_tile(native_byte_tile),.byte_lane(native_byte_lane),.byte_kind(native_byte_kind),.byte_generation(native_byte_generation),
 .tx_valid(native_tx_valid),.tx_ready(native_tx_ready),.tx_data(native_tx_data),
 .ack_valid(native_ack_valid),.ack_ready(native_ack_ready),.ack_accept(native_ack_data[16]),.ack_generation(native_ack_data[15:0]),.busy(),.error(native_export_error));
nes_native_mailbox165 #(.WIDTH(96)) native_records(
 .src_clk(clk),.dst_clk(host_clk),.reset(reset),.src_valid(native_tx_valid),.src_ready(native_tx_ready),.src_data(native_tx_data),
 .dst_valid(native_host_valid),.dst_ready(native_host_ready),.dst_data(native_host_data));
nes_native_mailbox165 #(.WIDTH(17)) native_prepared(
 .src_clk(host_clk),.dst_clk(clk),.reset(reset),.src_valid(native_host_ack_valid),.src_ready(native_host_ack_ready),.src_data({native_host_ack_accept,native_host_ack_generation}),
 .dst_valid(native_ack_valid),.dst_ready(native_ack_ready),.dst_data(native_ack_data));
'''

def prepare(evidence,out):
 inputs=memory_prepare(evidence,out);p=out/'nes_live_joint.sv';s=p.read_text()
 assert s.count(FRAME_PORTS)==1 and s.count(FILL_PORTS)==1
 s=s.replace(FRAME_PORTS,PORTS).replace(FILL_PORTS,'')
 internal=(FRAME_PORTS+FILL_PORTS).replace(',input wire',';input wire').replace(',output wire',';output wire').replace('input wire','wire').replace('output wire','wire').replace(',\n',';\n')
 s=s.replace('wire native_fill_slot,',internal+'\nwire native_fill_slot,',1)
 assert s.count('endmodule')==1;s=s.replace('endmodule',BINDING+'\nendmodule')
 p.write_text(s)
 for n in FILES:shutil.copy2(ROOT/'src/nes/diagnostic'/n,out/n)
 return inputs
