# SPDX-License-Identifier: MIT
"""F8 queue status: checked credits and live tile/map token ownership."""
from nes_mux258 import sources as prior
from nes_delta231 import once

def sources():
 src=prior();q=src['nes_queue258.sv']
 q=once(q,' output reg ack_done,',' input wire [127:0] progress_status,\n output reg ack_done,')
 q=q.replace('ack_work,completed_ack','ack_work').replace('completed_ack<=0;','').replace('completed_ack<=ack_work;','')
 q=q.replace('[151:0] snapshot','[183:0] snapshot').replace('snapshot[151-crc_position*8','snapshot[183-crc_position*8')
 q=q.replace('crc_position==17','crc_position==21').replace('byte_count<=19','byte_count<=23').replace('8*(19-byte_count)','8*(23-byte_count)').replace('byte_count!=20','byte_count!=24')
 q=once(q,"      snapshot[151:144]<=8'hf7;snapshot[143:136]<=flags;\n      snapshot[135:120]<=accepted;snapshot[119:104]<=retired;snapshot[7:0]<=0;", "      snapshot[183:176]<=8'hf8;snapshot[175:168]<=flags;\n      snapshot[167:152]<=accepted;snapshot[151:136]<=retired;snapshot[135:8]<=progress_status;snapshot[7:0]<=0;")
 q=once(q,"      for(j=0;j<12;j=j+1)snapshot[103-j*8-:8]<=ack_valid?completed_ack[j*8+:8]:8'd0;",'')
 m=src['nes_mux258.sv']
 m=once(m,' reg qretire;wire qr,qfault,qdone;', ' reg tiles_closed;\n reg qretire;wire qr,qfault,qdone;')
 m=once(m,'nes_queue258 queue(','''wire [127:0] progress_status={
  5'd0,owner==MAP,chunk_ready,tiles_closed,
  allocation[7:0],allocation[15:8],allocation[23:16],allocation[31:24],
  chunk_token[7:0],chunk_token[15:8],chunk_token[23:16],chunk_token[31:24],
  chunk_length[7:0],4'd0,chunk_length[11:8],5'd0,identity[48],owner==MAP,tkind&&owner==TILE,
  tslot[7:0],6'd0,tslot[9:8],identity[39:32],identity[47:40]};
 nes_queue258 queue(.progress_status(progress_status),''')
 a=m.index('wire [127:0] progress_status=');b=m.index(';\n nes_queue258',a)+1
 progress=m[a:b].replace('wire [127:0] progress_status=','assign progress_status=')
 m=m[:a]+'wire [127:0] progress_status;'+m[b:]
 m=once(m,' wire tile_consume,map_consume;', ' '+progress+'\n wire tile_consume,map_consume;')
 m=m.replace('header[0]!=9','header[0]!=12').replace('header[0]>9','header[0]>13')
 m=once(m,"header[1]!={7'd0,identity[48]}||", "(header[0]==12&&header[1]!={7'd0,identity[48]})||")
 m=once(m,'state<=IDLE;owner<=NONE;failed<=0;', 'state<=IDLE;owner<=NONE;failed<=0;tiles_closed<=0;')
 m=once(m,'identity<=idata;have_identity<=1;', 'identity<=idata;have_identity<=1;tiles_closed<=0;')
 m=once(m,'if(tend)tile_ended<=1;', 'if(tend)begin tile_ended<=1;tiles_closed<=1;end')
 m=once(m,'if(owner==NONE&&have_identity&&state!=DONE)begin', 'if(tiles_closed&&trequest)failed<=1;\n    if(owner==NONE&&have_identity&&state!=DONE)begin')
 t=src['nes_tile_producer258.sv']
 t=once(t,'state==CHECK&&wend&&!opened&&in_frame&&wgen==frame_gen', 'state==CHECK&&wend&&!opened&&(!in_frame||wgen==frame_gen)')
 t=once(t,'||(wend&&!in_frame)','')
 t=once(t,'sealed_generation<=frame_gen;in_frame<=0;', 'sealed_generation<=wgen;in_frame<=0;')
 src.update({'nes_queue258.sv':q,'nes_mux258.sv':m,'nes_tile_producer258.sv':t})
 return {n.replace('258','259'):s.replace('nes_queue258','nes_queue259').replace('nes_mux258','nes_output259').replace('nes_tile_producer258','nes_tile_producer259') for n,s in src.items()}
