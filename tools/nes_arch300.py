"""Aligned metadata RAM and common original-descriptor exclusive-end datapath."""
import re
from nes_delta231 import once

def apply(d):
    p=d/'nes_mux260.sv';s=p.read_text()
    decl=" wire [16:0] descriptor_end287={1'b0,startpos}+{1'b0,outlen};"
    s=once(s,decl,'')
    s=once(s,' reg bad_data278;',decl+'\n reg bad_data278;')
    assert s.count('startpos+outlen')==7
    s=s.replace('startpos+outlen','descriptor_end287')
    # Replace first->count->end round trip with a descriptor-exclusive end.
    s=s.replace('ordinary_count','ordinary_end300')
    s=once(s,'assign ordinary_end300=receipt_count282;', 'assign ordinary_end300=receipt_limit287;')
    s=once(s,'reg [11:0] receipt_first282,receipt_count282;', 'reg [11:0] receipt_first282;')
    s=once(s,'receipt_first282=0;receipt_count282=0;', 'receipt_first282=0;')
    s=once(s,'   receipt_count282=receipt_limit287-receipt_first282;\n   receipt_valid282=receipt_count282!=0;',
               '   receipt_valid282=receipt_limit287>receipt_first282;')
    p.write_text(s,newline='\n')
    p=d/'nes_joint266.sv';s=p.read_text().replace('.ordinary_count(v_count)', '.ordinary_end300(v_count)');p.write_text(s,newline='\n')
    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,"wire [12:0] range_end283={1'b0,v_first}+{1'b0,v_count};",
      "wire [12:0] range_end283=v_descriptor287?{1'b0,v_count}:({1'b0,v_first}+{1'b0,v_count});")
    s=once(s,'||!v_count||range_end283>', '||(v_descriptor287?range_end283<={1\'b0,v_first}:!v_count)||range_end283>')
    # Keep independent domain, duplicate, CRC and map-order tests unchanged.
    s=once(s,"wire [9:0] hash_base=10'd332+{4'd0,v_bank,5'd0};", "wire [9:0] hash_base={4'b0111,v_bank,5'b00000};")
    s=once(s,"wire [9:0] v_validbase=v_bank?10'd166:10'd0;", "wire [9:0] v_validbase={1'b0,v_bank,8'd0};")
    # Context32 + offset4 retain order and relative meaning.
    s=re.sub(r"(?<![0-9])(83[2-9]|84[0-9]|85[0-9]|86[0-7])(?![0-9])",lambda m:str(int(m[0])-152),s)
    s=s.replace("10'd562","10'd768").replace("10'd396","10'd512")
    s=once(s,'V_CLEARALL:if(cursor==817)','V_CLEARALL:if(cursor==1023)') # reset initialization before source admission
    s=once(s,'cursor<=396','cursor<=512')
    s=once(s,'V_CLEARFRAME:if(cursor==817)', 'V_CLEARFRAME:if(cursor==1023)')
    s=once(s,'end end else cursor<=cursor+1\'b1;\n    V_RAWINVALID:',
      "end end else cursor<=cursor==677?10'd768:cursor+1'b1;\n    V_RAWINVALID:")
    s=once(s,'cursor<=314','cursor<=404');s=once(s,'cursor==331','cursor==421')
    p.write_text(s,newline='\n')

def observe(s):
    s=s.replace('dut.core.ram_b_we&&dut.core.ram_b_addr>867',"dut.core.ram_b_we&&dut.core.validator.state!=dut.core.validator.V_CLEARALL&&!((dut.core.ram_b_addr<166)||(dut.core.ram_b_addr>=256&&dut.core.ram_b_addr<=421)||(dut.core.ram_b_addr>=448&&dut.core.ram_b_addr<=677)||(dut.core.ram_b_addr>=680&&dut.core.ram_b_addr<=715)||(dut.core.ram_b_addr>=768))")
    s=s.replace('dut.flow.ordinary_count','(dut.flow.ordinary_end300-dut.flow.ordinary_first)')
    # Remap logical oracle accesses only; physical1024B STOP snapshots stay exact.
    for a,b in [('560+dut.crc_index278/8','676+dut.crc_index278/8'),('332+i','448+i'),('864+j','712+j'),
                ('i<332?i:i+64','addr300(i<332?i:i+64)')]:
        s=s.replace('dut.core.memory['+a+']','dut.core.memory['+b+']')
    lines=[]
    for line in s.splitlines():
        if ('j<818' in line or 'j<396' in line):line=line.replace('dut.core.memory[j]','dut.core.memory[addr300(j)]')
        lines.append(line)
    s='\n'.join(lines)+'\n'
    return once(s,' task clear_output;', '''
 function automatic integer addr300(input integer a);
  if(a<166)addr300=a;else if(a<332)addr300=a+90;
  else if(a<396)addr300=a+116;else if(a<562)addr300=a+116;
  else if(a<818)addr300=a+206;else if(a>=832&&a<868)addr300=a-152;else addr300=a;
 endfunction
 task clear_output;''')

def native(d):
    from nes_wait296 import prepare
    prepare(d)
    p=d/'nes_refill267.c';s=p.read_text()
    s=once(s,'  plan_cache282=0;wait_armed284=0;plan_at267+=len+3;plan_sent267++;', '''  plan_cache282=0;wait_armed284=0;plan_at267+=len+3;plan_sent267++;
  /* First publish BG, then produce OBJ while that bank/ROM can progress.
   * The original bounded two-bank loop supplies the newly completed batch. */
  if(prefill_active287){
   if(!service296()){plan_error267=5;return 0;}
   plan_bytes267=output_size285>plan_bytes267?output_size285:plan_bytes267;
  }''')
    p.write_text(s,newline='\n')
