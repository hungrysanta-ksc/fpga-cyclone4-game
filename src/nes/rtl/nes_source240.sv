// SPDX-License-Identifier: MIT
// Functional replacement candidate: actual collector queries -> speculative
// base/delta encoding -> two-bank SPI. Query235 is reused, not yet state-fused
// or whole-board resource approved. No connection to cartridge save SRAM.
module nes_source240(
 input wire clk,host_clk,reset,abort_source,start,output wire start_ready,
 input wire frame_owned,geometry_valid,input wire [15:0] frame_generation,
 input wire [31:0] content_epoch,frame_serial,
 input wire [2:0] patch_count,input wire [7:0] row_count,object_count,exception_count,
 input wire [5:0] group_count,palette_count,
 output wire query,output wire [2:0] query_kind,output wire [12:0] query_index,
 output wire [15:0] query_generation,input wire response,hit,input wire [63:0] data,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,output wire selected,miso,
 output wire done,output wire [3:0] fault
);
 wire qstart,estart,qquery,rquery,valid,ready,qdone,record_valid,record_ready,record_flush,byte_valid,byte_ready;
 wire [2:0] qkind;wire [12:0] qindex,rindex,offset;wire [15:0] qgen,ack_gen;
 wire [7:0] value,record_length,byte_data;wire [3:0] qfault,efault;
 wire ack_valid,ack_ready,ack_accept,sfault,hfault;
 assign fault=efault?efault:qfault?qfault:sfault?4'd7:4'd0;
 wire cancel=abort_source||sfault||qfault!=0||efault!=0;
 assign start_ready=qstart&&estart&&!cancel;
 assign query=qquery||rquery;assign query_kind=rquery?3'd7:qkind;
 assign query_index=rquery?rindex:qindex;assign query_generation=rquery?frame_generation:qgen;
 nes_source_query235 reader(.clk(clk),.reset(reset),.abort_source(cancel),.start(start&&start_ready),.start_ready(qstart),
  .frame_owned(frame_owned),.geometry_valid(geometry_valid),.frame_generation(frame_generation),.patch_count(patch_count),
  .row_count(row_count),.object_count(object_count),.exception_count(exception_count),.group_count(group_count),.palette_count(palette_count),
  .query(qquery),.query_kind(qkind),.query_index(qindex),.query_generation(qgen),.response(response),.hit(hit),.data(data),
  .out_valid(valid),.out_ready(ready),.out_data(value),.out_offset(offset),.done(qdone),.fault(qfault));
 nes_source_encoder240 encoder(.clk(clk),.reset(reset),.abort_source(cancel),.start(start&&start_ready),.start_ready(estart),
  .frame_owned(frame_owned),.geometry_valid(geometry_valid),.frame_generation(frame_generation),.content_epoch(content_epoch),.frame_serial(frame_serial),
  .patch_count(patch_count),.in_valid(valid),.in_ready(ready),.in_data(value),.in_offset(offset),
  .raw_query(rquery),.raw_index(rindex),.raw_response(response),.raw_hit(hit),.raw_data(data),
  .record_valid(record_valid),.record_ready(record_ready),.record_length(record_length),.record_flush(record_flush),
  .byte_valid(byte_valid),.byte_ready(byte_ready),.byte_data(byte_data),
  .ack_valid(ack_valid),.ack_ready(ack_ready),.ack_accept(ack_accept),.ack_generation(ack_gen),.done(done),.fault(efault));
 nes_source_spi235 transport(.src_clk(clk),.host_clk(host_clk),.reset(reset),.abort_source(cancel),
  .record_valid(record_valid),.record_ready(record_ready),.record_length(record_length),.record_flush(record_flush),
  .byte_valid(byte_valid),.byte_ready(byte_ready),.byte_data(byte_data),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
  .selected(selected),.miso(miso),.ack_valid(ack_valid),.ack_ready(ack_ready),.ack_accept(ack_accept),.ack_generation(ack_gen),
  .source_fault(sfault),.host_fault(hfault));
endmodule
