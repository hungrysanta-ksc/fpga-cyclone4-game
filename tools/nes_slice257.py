# SPDX-License-Identifier: MIT
"""Bounded R1 range integration: phase lease and DMA-completed receipt.

The one-range consumer is diagnostic. Other frame ranges/H2 remain255 fixtures.
"""
from nes_joint255 import sources as prior
from nes_delta231 import once, ROOT


def sources():
    src = prior()
    core = src['nes_core255.sv']
    extra = '''
 input wire display_lease,input wire [15:0] display_generation,input wire [31:0] display_epoch,
 input wire range_external,range_dma_done,
'''
    core = once(core, ' input wire clk,reset,abort_source,start,', extra+' input wire clk,reset,abort_source,start,')
    core = once(core, ' wire live,lease_ok;', ' reg external_range;\n wire live,lease_ok;')
    core = once(core, 'assign lease_ok=frame_owned&&geometry_valid&&generation==frame_generation;',
        'assign lease_ok=(output_phase&&!done)?(display_lease&&display_generation==generation&&display_epoch==epoch):(frame_owned&&geometry_valid&&generation==frame_generation);')
    core = once(core, 'state<=V_CLEARALL;v_bank<=0;', 'state<=V_CLEARALL;external_range<=0;v_bank<=0;')
    core = once(core, 'expanded<=0;state<=V_STREAM;', 'expanded<=0;external_range<=range_external;state<=V_STREAM;')
    core = once(core, 'V_STREAM:if(stream_valid&&stream_ready)begin',
        'V_STREAM:if(external_range&&range_dma_done)state<=V_RREAD;else if(!external_range&&stream_valid&&stream_ready)begin')
    core = core.replace('lease_ok&&state==V_STREAM&&', 'lease_ok&&!external_range&&state==V_STREAM&&')
    core = once(core, 'else if(!fault&&state==V_STREAM&&',
        'else if(!fault&&range_dma_done&&(state!=V_STREAM||!external_range))fault<=9;\n   else if(!fault&&state==V_STREAM&&')
    top = src['nes_joint255.sv']
    top = once(top, 'input wire host_clk', extra+'input wire host_clk')
    pp = ['display_lease','display_generation','display_epoch','range_external','range_dma_done']
    top = once(top, 'nes_core255 encoder(', 'nes_core255 encoder('+','.join('.'+n+'('+n+')' for n in pp)+',')
    top = once(top, 'frame_owned&&geometry_valid&&output_phase;', 'display_lease&&output_phase;')
    src['nes_core255.sv'] = core
    src['nes_joint255.sv'] = top
    # Do not replace decimal255 bitmap constants.
    src = {n.replace('255','257'):s.replace('nes_joint255','nes_joint257').replace('nes_core255','nes_core257').replace('nes_transport255','nes_transport257') for n,s in src.items()}
    q = (ROOT/'src/nes/diagnostic/nes_sink_queue184.sv').read_text()
    q = q.replace('nes_sink_queue184','nes_queue257')
    q = once(q, ' input wire clk,reset,enable,', ' input wire parser_retire,\n input wire clk,reset,enable,')
    q = once(q, '   if(ack_write&&enable&&!fault)begin', '''
   if(parser_retire&&enable&&!fault)begin
    if(!packet_ready||ack_write||ack_publish||checking)fault<=1;
    else retired<=retired+1'b1;
   end
   if(ack_write&&enable&&!fault)begin''')
    src['nes_queue257.sv'] = q
    src['nes_range257.sv'] = (ROOT/'src/nes/rtl/nes_range257.sv').read_text()
    return src
