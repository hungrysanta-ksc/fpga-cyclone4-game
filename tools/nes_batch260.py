# SPDX-License-Identifier: MIT
"""Multi-range packet holds its queue head through every DMA and receipt."""
from nes_output259 import sources as prior
from nes_delta231 import once

def sources():
 src=prior();m=src['nes_mux259.sv']
 m=once(m,'DONE=16;', 'DONE=16,DREAD=17,DCAP=18,DCHECK=19,BRET=20;')
 m=once(m,'reg [7:0] header[0:19];', 'reg batch;reg [7:0] remaining;reg [8:0] cursor;\n reg [7:0] header[0:20];')
 m=once(m,'length<=0;first<=0;', 'batch<=0;remaining<=0;cursor<=0;length<=0;first<=0;')
 m=once(m,'if(at==19||(at==15&&header[0]!=12))', 'if((at==20&&header[0]==14)||(at==19&&header[0]==12)||(at==15&&header[0]!=12&&header[0]!=14))')
 m=once(m,'header[0]>13','header[0]>14')
 m=once(m,'(header[0]==12&&header[1]', '((header[0]==12||header[0]==14)&&header[1]')
 m=once(m,'else if(header[0]!=12)state<=NORMAL;', '''else if(header[0]==14)begin
       if(qlen<26||{header[13],header[12]}!={7'd0,qlen}-16'd16||header[14]!=0||header[15]!=0||
        header[20]==0||header[20]>47||{header[19],header[18],header[17],header[16]}>32'hffffffff-{24'd0,header[20]})failed<=1;
       else begin batch<=1;remaining<=header[20];cursor<=21;parser_address<=21;at<=0;
        token<={header[19],header[18],header[17],header[16]};map_receipt<=0;state<=DREAD;end
      end
      else if(header[0]!=12)state<=NORMAL;''')
 m=once(m,'else begin first<={header[11][3:0],header[10]};', 'else begin batch<=0;first<={header[11][3:0],header[10]};')
 m=once(m,'OPEN:if(owner==MAP)begin', '''DREAD:state<=DCAP;
     DCAP:begin
      header[10+at]<=qdata;cursor<=cursor+1'b1;parser_address<=parser_address+1'b1;
      if(at==2)state<=DCHECK;else begin at<=at+1'b1;state<=DREAD;end
     end
     DCHECK:begin
      if(header[11]>15||header[10][0]||header[12]==0||header[12]>64||header[12][0]||
       {header[11],header[10]}+{8'd0,header[12]}>4096||
       cursor+{1'b0,header[12]}+(remaining>1?9'd5:9'd0)>qlen||
       (remaining==1&&cursor+{1'b0,header[12]}!=qlen))failed<=1;
      else begin first<={1'b0,header[11][3:0],header[10][7:1]};length<={4'd0,header[12]};count<=header[12]>>1;
       cursor<=cursor+{1'b0,header[12]};map_receipt<=0;state<=OPEN;end
     end
     OPEN:if(owner==MAP)begin''')
 m=once(m,'at<=0;parser_address<=20;state<=PREAD;', 'at<=0;if(!batch)parser_address<=20;state<=PREAD;')
 m=once(m,'SEAL:state<=RETIRE;', 'SEAL:state<=batch?DMA:RETIRE;')
 m=once(m,'CONSUME:begin state<=IDLE;owner<=NONE;last_map_token<=token;map_receipt<=1;end', '''CONSUME:begin
      last_map_token<=token;map_receipt<=1;
      if(batch&&remaining>1)begin remaining<=remaining-1'b1;token<=token+1'b1;at<=0;parser_address<=cursor[7:0];state<=DREAD;end
      else begin owner<=NONE;
       if(batch)begin qretire<=1;packet_seq<=packet_seq+1'b1;state<=BRET;end
       else state<=IDLE;
      end
     end
     BRET:state<=IDLE;''')
 src['nes_mux259.sv']=m
 return {n.replace('259','260'):s.replace('nes_output259','nes_output260').replace('nes_queue259','nes_queue260').replace('nes_tile_producer259','nes_tile_producer260') for n,s in src.items()}
