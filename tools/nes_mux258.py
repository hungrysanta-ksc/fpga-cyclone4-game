# SPDX-License-Identifier: MIT
"""Expose the actual206 tile producer and connect one shared staging owner."""
from nes_slice257 import sources as prior
from nes_delta231 import BASE,ROOT,once


def sources():
    src=prior()
    q=src['nes_queue257.sv'].replace('nes_queue257','nes_queue258')
    q=once(q,' input wire parser_retire,',' output reg ack_done,\n input wire parser_retire,')
    q=once(q,'accepted<=0;retired<=0;','ack_done<=0;accepted<=0;retired<=0;')
    q=once(q,'  end else begin\n   ss<=','  end else begin\n   ack_done<=0;\n   ss<=')
    q=once(q,'retired<=retired+1\'b1;completed_ack<=','ack_done<=1;retired<=retired+1\'b1;completed_ack<=')
    t=(BASE/'probes/nes-source240/board01/nes_tile_bulk206.sv').read_text()
    t=t.replace('nes_tile_bulk206','nes_tile_producer258')
    t=once(t,' input wire nes_clk,host_clk,reset,active,stop,source_fault,', '''
 output wire request_stage,input wire grant_stage,
 output wire p_begin,p_put,p_seal,output wire [7:0] p_data,
 input wire begin_ready,put_ready,producer_error,
 input wire chunk_ready,input wire [11:0] chunk_length,input wire [31:0] chunk_token,
 input wire nes_clk,host_clk,reset,active,stop,source_fault,''')
    t=once(t,' output wire chunk_ready,output wire [11:0] chunk_length,output wire [31:0] chunk_token,','')
    t=once(t,'input wire consume_token,output wire consume_error,','input wire consume_token,') if 'input wire consume_token,output wire consume_error,' in t else t
    t=once(t,'input wire [31:0] consume_token,output wire consume_error,','input wire [31:0] consume_token,')
    t=once(t,' input wire [23:0] address,input wire read_n,write_n,\n output wire [7:0] data_out,output wire oe_n,dir,','')
    t=once(t,'reg [4:0] at;reg [31:0] token;','reg [4:0] at;wire [31:0] token=token_seed;')
    t=once(t,' wire begin_ready,put_ready,producer_error;','')
    start=t.index(' nes_bulk_aperture188 #(');end=t.index(' always @(posedge host_clk or posedge hr)',start)
    t=t[:start]+''' assign request_stage=word_valid;
 assign p_begin=state==OPEN&&!hc&&grant_stage&&token!=32'hffffffff;
 assign p_put=state==WRITE&&!hc&&grant_stage;
 assign p_data=read_data;assign p_seal=state==SEAL&&!hc&&grant_stage;
'''+t[end:]
    t=once(t,'token<=0;','')
    t=once(t,'INIT:begin token<=token_seed;state<=CHECK;end','INIT:state<=CHECK;')
    t=once(t,'token<=token+1\'b1;','')
    t=once(t,'assign word_ready=!hc&&word_valid&&','assign word_ready=!hc&&grant_stage&&word_valid&&')
    t=once(t,'   if(!hc)begin','   if(!hc&&grant_stage)begin')
    # Payload/descriptor logic is unchanged; only the aperture boundary and
    # token allocation move into the owner shared with the map parser.
    src['nes_queue258.sv']=q;src['nes_tile_producer258.sv']=t
    src['nes_mux258.sv']=(ROOT/'src/nes/rtl/nes_mux258.sv').read_text()
    return {n:s for n,s in src.items() if n not in ['nes_queue257.sv','nes_range257.sv']}
