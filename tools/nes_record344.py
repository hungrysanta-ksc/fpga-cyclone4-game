# SPDX-License-Identifier: MIT
"""NES344 contiguous source records, byte-identical MASK/SHIFT ABI."""
from nes_delta231 import once

def apply(d):
 p=d/'nes_core257.sv';s=p.read_text()
 s=once(s,'IDLE,HEADER,FETCH,FSTORE,BLOCKEND,REQUEST','IDLE,HEADER,FETCH,FSTORE,BLOCKEND,BUILD344,REQUEST')
 s=once(s,"  if(kind==MASK)a_addr=rec_i<=mask_bytes?9'd383+rec_i:{1'b0,rec_i}-9'd1-{5'd0,mask_bytes};",'')
 s=once(s,"a_addr={2'd0,diff_count};a_we=changed;a_w=new_byte;","a_addr=9'd257+{5'd0,mask_bytes}+{2'd0,diff_count};a_we=changed;a_w=new_byte;")
 s=once(s,"b_addr=9'd384+{5'd0,row_i[6:3]};","b_addr=9'd257+{5'd0,row_i[6:3]};")
 s=once(s,'   GEOTRAILER,ENDTRAILER:begin', '''   BUILD344:begin
    a_addr=9'd256+build_i;a_we=1;
    case(build_i)
     0:a_w={kind==SHIFT,block_id};1:a_w=shift_left?1:255;
     2:a_w=shift_left?new2:edge0;default:a_w=shift_left?new1:edge1;
    endcase
   end
   GEOTRAILER,ENDTRAILER:begin''')
 a=s.index('  if(kind==MASK&&rec_i==0)');b=s.index('  if(kind==GEO||kind==ENDREC)',a);s=s[:a]+s[b:]
 s=once(s,'if(shift_ok)begin shift_left<=left_row;emit_record(SHIFT,4);end\n     else emit_record(MASK,{1\'b0,diff_count}+{4\'d0,mask_bytes}+8\'d1);', '''if(shift_ok)begin shift_left<=left_row;kind<=SHIFT;record_length<=4;end
     else begin kind<=MASK;record_length<={1'b0,diff_count}+{4'd0,mask_bytes}+8'd1;end
     build_i<=0;record_flush<=0;rec_i<=0;state<=BUILD344;''')
 s=once(s,'    REQUEST:if(record_ready)', '''    BUILD344:if(kind==MASK||build_i==3)state<=REQUEST;else build_i<=build_i+1'b1;
    REQUEST:if(record_ready)''')
 p.write_text(s,newline='\n')

def native(d):
 from nes_read336 import native as old
 old(d);p=d/'nes_planner285.c';s=p.read_text()
 s=once(s,'static unsigned reserve_bytes293,reserve_plans293;', 'static unsigned reserve_bytes293,reserve_plans293;\nunsigned prefixes344,run_first344,run_last344;\nextern unsigned prefill287(void);')
 at=s.index('static bool emit285(')
 s=s[:at]+'''/* Publish one already complete contiguous run, never speculative slots.
 * Allocator used slots cannot be rewritten/evicted within this generation. */
__attribute__((noinline)) unsigned advance344(void){
 if(input285.state!=NES_NATIVE165_COMMITTED||resident285.fault||!resident285.open)return 0;
 if(prefixes344||resident285.serial<=2||batch_count285<3)return 1;
 unsigned bytes=0,plans=0,first=0,last=0;
 if(order247_key(batch285)==0){bytes=order247_length(batch285);plans=1;}
 unsigned start=bytes;
 while(bytes<batch_size285){
  unsigned key=order247_key(batch285+bytes);
  if(key==0||key>=1024||(bytes!=start&&key!=last+1))break;
  if(!(resident285.used[key/8]&(1u<<(key%8))))return 0;
  if(bytes==start)first=key;last=key;
  bytes+=order247_length(batch285+bytes);plans++;
 }
 if(!first||last==first)return 1;
 if(output_size285+bytes+3>sizeof output285)return 0;
 output285[output_size285++]=bytes;output285[output_size285++]=bytes>>8;output285[output_size285++]=plans;
 memcpy(output285+output_size285,batch285,bytes);output_size285+=bytes;
 memmove(batch285,batch285+bytes,batch_size285-bytes);batch_size285-=bytes;batch_count285-=plans;
 reserve_bytes293+=bytes;reserve_plans293+=plans;prefixes344=1;run_first344=first;run_last344=last;
 trace259(2,plans);return prefill287()!=0;
}
''' +s[at:]
 s=once(s,'unsigned begin285(void){','unsigned begin285(void){prefixes344=run_first344=run_last344=0;')
 s=once(s,'unsigned bytes=batch_size285,plans=batch_count285;','unsigned bytes=batch_size285+reserve_bytes293,plans=batch_count285+reserve_plans293;')
 p.write_text(s,newline='\n');p=d/'nes_input286.inc';s=p.read_text()
 s=once(s,'if(result==1&&bg_done293()&&!flush_bg293())','if(result==1&&!bg_done293()&&!advance344())return 0;if(result==1&&bg_done293()&&!flush_bg293())')
 s=once(s,'void stop286(void){','void stop286(void){prefixes344=run_first344=run_last344=0;reserve_bytes293=reserve_plans293=0;')
 p.write_text(s,newline='\n')
