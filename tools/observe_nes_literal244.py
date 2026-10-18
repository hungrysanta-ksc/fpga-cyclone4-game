# SPDX-License-Identifier: MIT
"""Read-only simulation observer: actual240 FLUSH through actual SBYTE acceptance."""
from nes_operand243 import LAYOUT,FIELDS

def observe_flush(source):
    fields=[]
    for n,addresses in LAYOUT.items():
        width=8*len(addresses)
        fields.append(('{'+str(width-FIELDS[n])+"'b0,"+n+'}') if FIELDS[n]<width else n)
    packed='{'+','.join(reversed(fields))+'}'
    observer='''
 integer lf_fd,lf_seen=0,lf_i,lf_length=0,lf_index=0,lf_result=0,lf_cases=0;
 reg lf_open=0,lf_sending=0,lf_record;
 reg [15:0] lf_flags;
 reg [191:0] lf_before,lf_after;
 reg [95:0] lf_c0,lf_c1;reg [1919:0] lf_l0,lf_l1;reg [1943:0] lf_packet;
 initial lf_fd=$fopen("flush-observed.txt","w");
 task automatic lf_dump;begin
  $fwrite(lf_fd,"%04x %0d %048x %048x %024x %0480x %024x %0480x %0d %0486x\\n",
    lf_flags,lf_result,lf_before,lf_after,lf_c0,lf_l0,lf_c1,lf_l1,lf_length,lf_packet);
  $fflush(lf_fd);lf_cases=lf_cases+1;lf_open=0;lf_sending=0;
 end endtask
 always @(posedge clk)begin
  if(reset||abort_source||fault||!lease_ok)begin lf_open=0;lf_sending=0;end
  else begin
   if(state==FLUSH&&!lf_open)begin
    lf_seen=lf_seen+1;
    if(lf_seen<=64||lf_seen%17==0)begin
     lf_open=1;lf_sending=0;lf_flags={14'b0,raw_mode,raster_mode};lf_before=PACKED;
     lf_record=lit_used!=0&&!raster_mode;lf_length=lf_record?lit_used+3:0;lf_index=0;lf_packet=0;
     lf_result=lit_used!=0&&raster_mode&&cheap_cost+3+lit_used>=13?1:0;
     for(lf_i=0;lf_i<12;lf_i=lf_i+1)lf_c0[lf_i*8+:8]=scratch[80+lf_i];
     for(lf_i=0;lf_i<240;lf_i=lf_i+1)lf_l0[lf_i*8+:8]=scratch[256+lf_i];
    end
   end
   if(lf_open&&!lf_sending&&((state==FLUSH&&(!lit_used||(raster_mode&&cheap_cost+3+lit_used>=13)))||state==LDONE))begin
    #1;lf_after=PACKED;
    for(lf_i=0;lf_i<12;lf_i=lf_i+1)lf_c1[lf_i*8+:8]=scratch[80+lf_i];
    for(lf_i=0;lf_i<240;lf_i=lf_i+1)lf_l1[lf_i*8+:8]=scratch[256+lf_i];
    if(lf_record)lf_sending=1;else lf_dump();
   end else if(lf_sending&&state==SBYTE&&byte_ready)begin
    lf_packet[lf_index*8+:8]=byte_data;lf_index=lf_index+1;
    if(lf_index==lf_length)lf_dump();
   end
  end
 end
'''.replace('PACKED',packed)
    assert source.count('endmodule')==1
    return source.replace('endmodule',observer+'\nendmodule')
