# SPDX-License-Identifier: MIT
"""Integrated source/query/phase RAM, output batch DMA receipts and display lease.

The non-map stream and H2/context/check ports remain explicit, unimplemented
producer boundaries. They are not tied off or credited as recovered hardware.
"""
import re
from nes_batch260 import sources as prior
from nes_delta231 import once


def sources():
 src=prior()
 # Expose the real E0/E1 owner to the shared SPI MISO arbiter.
 src['nes_mux260.sv']=once(src['nes_mux260.sv'],'output wire miso,','output wire miso,output wire selected,')
 src['nes_mux260.sv']=once(src['nes_mux260.sv'],'.selected(),.miso(miso)', '.selected(selected),.miso(miso)')
 core=src['nes_joint257.sv'];header=core[:core.index(');')]
 ports=[];direction=width=None
 for part in header[header.index('(')+1:].split(','):
  part=part.strip();m=re.fullmatch(r'(input|output) wire\s*(\[[^\]]+\])?\s*(\w+)',part)
  if m:direction,width,name=m.groups()
  else:
   assert re.fullmatch(r'\w+',part),part
   name=part
  ports.append((direction,width or '',name))
 internal={'display_lease','display_generation','display_epoch','range_external','range_dma_done','v_display_ack'}
 declarations=[f'{d} wire {w} {n}' for d,w,n in ports if n not in internal]
 declarations += ['input wire capture_begin,source_ready,source_is_rom,source_writing,reader_drained',
  'output wire release_frame,lease_valid,waiting_display,lease_fault,retired,display_ack',
  'input wire identity_valid,output wire identity_ready,input wire bank',
  'input wire [23:0] address,input wire read_n,write_n,input wire [7:0] data_in',
  'output wire [7:0] data_out,output wire bus_valid,staged,receipt_committed,flow_fault',
  'input wire tile_valid,output wire tile_ready,input wire [7:0] tile_data',
  'input wire [4:0] tile_index,input wire [5:0] tile_length,input wire [1:0] tile_kind',
  'input wire [9:0] tile_slot,input wire [15:0] tile_generation',
  'input wire end_valid,output wire end_ready,input wire [15:0] end_generation',
  'output wire ordinary_ready,output wire [31:0] next_token']
 s='// SPDX-License-Identifier: MIT\nmodule nes_joint261 #(parameter SHARED=1)(\n'+',\n'.join(declarations)+'\n);\n'
 s+='''
 wire [15:0] display_generation;wire [31:0] display_epoch;
 wire rv,rdone;wire [11:0] rf,rc;
 wire source_selected,source_miso,output_selected,output_miso;
 wire cancel=abort_source||flow_fault||lease_fault;
 assign selected=source_selected||output_selected;
 assign miso=source_selected?source_miso:output_miso;
 nes_capture_lease201 lease(.clk(clk),.reset(reset),.stop(abort_source||flow_fault||fault!=0),
 .capture_begin(capture_begin),.frame_owned(frame_owned),.geometry_valid(geometry_valid),.frame_generation(frame_generation),
 .export_release(done),.export_error(fault),.source_ready(source_ready),.source_is_rom(source_is_rom),
 .source_writing(source_writing),.live_epoch(content_epoch),.reader_drained(reader_drained),
 .retire_commit(display_ack),.retire_generation(display_generation),.release_frame(release_frame),
 .lease_valid(lease_valid),.retire_permitted(),.export_permitted(),.captured_epoch(display_epoch),
 .captured_generation(display_generation),.waiting_display(waiting_display),.fault(lease_fault));
 nes_output260 #(.SHARED(SHARED)) flow(.nes_clk(clk),.host_clk(host_clk),.reset(reset),.cancel(abort_source||lease_fault||fault!=0),
 .identity_valid(identity_valid),.identity_ready(identity_ready),.serial(frame_serial),.generation(display_generation),.bank(bank),
 .SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),.miso(output_miso),.selected(output_selected),
 .address(address),.read_n(read_n),.write_n(write_n),.data_in(data_in),.data_out(data_out),.bus_valid(bus_valid),
 .tile_valid(tile_valid),.tile_ready(tile_ready),.tile_data(tile_data),.tile_index(tile_index),.tile_length(tile_length),
 .tile_kind(tile_kind),.tile_slot(tile_slot),.tile_generation(tile_generation),
 .end_valid(end_valid),.end_ready(end_ready),.end_generation(end_generation),
 .range_valid(rv),.range_ready(v_ready),.range_first(rf),.range_count(rc),.range_dma_done(rdone),
 .sealed(v_sealed),.core_idle(start_ready),.display_ack(display_ack),.retired(retired),.staged(staged),
 .receipt_committed(receipt_committed),.fault(flow_fault),.ordinary_ready(ordinary_ready),.next_token(next_token));
'''
 bound=dict(display_lease='lease_valid',display_generation='display_generation',display_epoch='display_epoch',
  range_external='rv',range_dma_done='rdone',v_display_ack='display_ack',abort_source='cancel',
  v_range_valid='v_range_valid||rv',v_map_range="rv?1'b1:v_map_range",v_first='rv?rf:v_first',v_count='rv?rc:v_count',
  selected='source_selected',miso='source_miso')
 s+='nes_joint257 core('+',\n'.join(f'.{n}({bound.get(n,n)})' for _,_,n in ports)+');\nendmodule\n'
 src['nes_joint261.sv']=s
 return src
