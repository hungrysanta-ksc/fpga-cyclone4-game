# SPDX-License-Identifier: MIT
"""NES348 fixed scan repeat source; preserves338 order and336 planner."""
from nes_delta231 import once

def source(d):
 from nes_record344 import apply
 apply(d)
 p=d/'nes_core257.sv';s=p.read_text()
 s=once(s,'{H,MASK,SHIFT,GEO,ENDREC}', '{H,MASK,SHIFT,GEO,ENDREC,REPEAT348}')
 s=once(s,'2:header_byte=2;', '2:header_byte=4;')
 s=once(s,' wire shift_ok=', ''' wire repeat348=block_id>=32&&(left_row||right_row);
 wire [7:0] repeat_length348=left_row?8'd3:8'd4;
 wire use_repeat348=repeat348&&repeat_length348<({1'b0,diff_count}+{4'd0,mask_bytes}+8'd1);
 wire shift_ok=''')
 s=once(s,'if(row_i>=2)begin if(base_q!=new2)left_row<=0;if(new_byte!=old2)right_row<=0;end', '''if(block_id<32)begin
      if(row_i>=2)begin if(base_q!=new2)left_row<=0;if(new_byte!=old2)right_row<=0;end
     end else begin
      if(row_i!=0&&new_byte!=edge0)left_row<=0;
      if(row_i>=2&&new_byte!=(row_i[0]?edge1:edge0))right_row<=0;
     end''')
 s=once(s,"expanded<=expanded+(shift_ok?16'd66:{9'd0,diff_count})", "expanded<=expanded+(use_repeat348?{9'd0,row_size}:shift_ok?16'd66:{9'd0,diff_count})")
 s=once(s,'if(shift_ok)begin shift_left<=left_row;kind<=SHIFT;record_length<=4;end', 'if(use_repeat348)begin kind<=REPEAT348;record_length<=repeat_length348;end\n     else if(shift_ok)begin shift_left<=left_row;kind<=SHIFT;record_length<=4;end')
 s=once(s,'    case(build_i)\n     0:a_w={kind==SHIFT,block_id};', '''    if(kind==REPEAT348)case(build_i)
     0:a_w={1'b1,block_id};1:a_w=left_row?1:2;2:a_w=edge0;default:a_w=edge1;
    endcase
    else case(build_i)
     0:a_w={kind==SHIFT,block_id};''')
 s=once(s,'BUILD344:if(kind==MASK||build_i==3)', 'BUILD344:if(kind==MASK||build_i+1==record_length)')
 s=once(s,'MASK,SHIFT:next_block()', 'MASK,SHIFT,REPEAT348:next_block()')
 s=once(s,'diff_count<=0;mask_acc<=0;q_have<=0;q_pending<=0;', 'diff_count<=0;mask_acc<=0;left_row<=1;right_row<=1;q_have<=0;q_pending<=0;')
 p.write_text(s,newline='\n')

def native(d):
 from nes_read336 import native as old
 from nes_fixed347 import decoder
 old(d)
 (d/'nes_decode280.c').write_text(decoder(),newline='\n')
