# SPDX-License-Identifier: MIT
"""Assembler and simulation-only240 operation observer for the UNBOUND243 kernel."""
from nes_operand242 import FIELDS

HOT={'row_i','old1','old2','new1','new2'}
LAYOUT={};at=104
for name,width in FIELDS.items():
    if name in HOT:continue
    LAYOUT[name]=list(range(at,at+(width+7)//8));at+=len(LAYOUT[name])
assert at==128
OPS=dict(HALT=0,LDI=1,LD=2,ST=3,ADD=4,ADC=5,ADDI=6,ADCI=7,ARG=8,
         XOR_RF=9,ANDI=10,OUT=11,JMP=12,FAIL=13,CMP=14,JZ=15,JC=16)

def assemble():
    words=[];labels={};fix=[];entries={}
    def label(n):assert n not in labels;labels[n]=len(words)
    def emit(op,v=0):
        if isinstance(v,str):fix.append((len(words),v));v=0
        assert 0<=v<8192;words.append((OPS[op]<<13)|v)
    def rf(op,n,i=0):emit(op,LAYOUT[n][i]-96)
    def begin(n):entries[n]=len(words)
    def clear(names):
        emit('LDI',0)
        for n in names:
            for i in range(len(LAYOUT[n])):rf('ST',n,i)
    def copy(a,b):
        for i in range(len(LAYOUT[a])):rf('LD',a,i);rf('ST',b,i)
    def argument(n,selector=0):
        for i in range(len(LAYOUT[n])):
            emit('ARG',selector+i)
            if i==1 and FIELDS[n]==13:emit('ANDI',31)
            rf('ST',n,i)
    begin('init');clear(['row_start','lit_at','lit_len','lit_used','gap','cheap_cost','rows','spans','expanded','build_i'])
    argument('raw_limit');emit('LDI',66);rf('ST','row_size');emit('HALT')
    begin('row_byte')
    emit('ARG',0);rf('ADD','row_start');rf('ST','byte_at')
    emit('ARG',1);rf('ADC','row_start',1);emit('ANDI',31);rf('ST','byte_at',1)
    argument('old_byte',2);emit('HALT')
    begin('count')
    rf('LD','spans');emit('ADDI',1);rf('ST','spans');rf('LD','spans',1);emit('ADCI',0);rf('ST','spans',1)
    emit('ARG',0);rf('ADD','expanded');rf('ST','expanded');emit('ARG',1);rf('ADC','expanded',1);rf('ST','expanded',1);emit('HALT')
    begin('mask');emit('ARG',0);rf('ST','xor_byte');emit('ARG',1);rf('XOR_RF','xor_byte');rf('ST','xor_byte');emit('HALT')
    begin('dispatch');argument('row_start');argument('row_size',2);emit('HALT')
    begin('raw_increment');rf('LD','lit_len');emit('ADDI',1);rf('ST','lit_len');rf('ST','lit_used');emit('HALT')
    begin('group_done');clear(['cheap_cost','lit_len','lit_used','gap','rows'])
    emit('LDI',5664&255);rf('CMP','row_start');emit('JZ','group_high');emit('JMP','group_copy')
    label('group_high');emit('LDI',5664>>8);rf('CMP','row_start',1);emit('JZ','group_end')
    label('group_copy');copy('row_start','group_start');label('group_end');emit('HALT')
    # A held output must survive independent operand writes and a blocked
    # second publication. Test-only entry, not a codec record microprogram.
    begin('publish');emit('ARG',0);emit('OUT');argument('expanded',2);rf('LD','expanded');emit('OUT');emit('HALT')
    begin('bad_rf');emit('LD',7);emit('HALT')
    begin('bad_opcode');emit('FAIL')
    for i,n in fix:words[i]|=labels[n]
    assert len(words)<=512
    return words,entries

def instrument240(source):
    # Prepared-operation replay: this observer does not alter the240 DUT.
    fields=[]
    for n,addresses in LAYOUT.items():
        if len(addresses)==2 and FIELDS[n]==13:fields.append("{3'b0,"+n+'}')
        elif FIELDS[n]<8:fields.append('{'+str(8-FIELDS[n])+"'b0,"+n+'}')
        else:fields.append(n)
    packed='{'+','.join(reversed(fields))+'}'
    observer='''
 // SIMULATION ONLY: sampled actual240 pre/post operations, not game traces.
 integer op_fd,op_cmd,op_seen[0:59],op_state,op_j;
 reg [15:0] op_arg0,op_arg1;reg [191:0] op_before;
 initial begin op_fd=$fopen("operations.txt","w");for(op_j=0;op_j<60;op_j=op_j+1)op_seen[op_j]=0;end
 always @(posedge clk)begin
  op_cmd=-1;op_arg0=0;op_arg1=0;op_state=state;
  if(!reset&&!abort_source&&!fault&&(state==IDLE||lease_ok))begin
   case(state)
    IDLE:if(start&&frame_owned&&geometry_valid&&frame_serial!=0&&frame_serial!=32'hffffffff&&
      ((!base_valid&&frame_serial==1)||(base_valid&&content_epoch==epoch&&frame_serial==serial)))begin op_cmd=0;op_arg0={patch_count,8'b0};end
    MAPLVALUE,RASTERVALUE:begin op_cmd=1;op_arg0=row_i;op_arg1=a_q;end
    SHIFTDONE:begin op_cmd=2;op_arg0=66;end
    RASTERDONE:begin op_cmd=2;op_arg0={rows,3'b0};end
    CHEAPDONE:begin op_cmd=2;op_arg0=record_length-3;end
    MASKVALUE,MASKSETVALUE:begin op_cmd=3;op_arg0={b_q,a_q};end
    DISPATCH:begin op_cmd=4;op_arg0=cursor;op_arg1=cursor==5741?row_size:(cursor<2112?66:8);end
    RAWWAIT:if(raw_response&&raw_hit&&raw_data[63:6]==0)op_cmd=5;
    GROUPDONE:op_cmd=6;
   endcase
  end
  if(op_cmd>=0)begin
   op_seen[op_state]=op_seen[op_state]+1;
   if(op_seen[op_state]<=64||op_seen[op_state]%257==0)begin
    op_before=PACKED;
    #1;$fwrite(op_fd,"%0d %04x %04x %048x %048x\\n",op_cmd,op_arg0,op_arg1,op_before,PACKED);$fflush(op_fd);
   end
  end
 end
'''.replace('PACKED',packed)
    assert source.count('endmodule')==1
    return '`timescale 1ns/1ps\n'+source.replace('endmodule',observer+'\nendmodule')

def reference(command,a,b,old):
    r=bytearray(old)
    def get(n):return int.from_bytes(bytes(r[x-104] for x in LAYOUT[n]),'little')
    def put(n,v):
        v&=(1<<FIELDS[n])-1
        for i,x in enumerate(LAYOUT[n]):r[x-104]=(v>>(8*i))&255
    if command==0:
        for n in ['row_start','lit_at','lit_len','lit_used','gap','cheap_cost','rows','spans','expanded','build_i']:put(n,0)
        put('raw_limit',a);put('row_size',66)
    elif command==1:put('byte_at',get('row_start')+a);put('old_byte',b)
    elif command==2:put('spans',get('spans')+1);put('expanded',get('expanded')+a)
    elif command==3:put('xor_byte',(a&255)^(a>>8))
    elif command==4:put('row_start',a);put('row_size',b)
    elif command==5:put('lit_len',get('lit_len')+1);put('lit_used',get('lit_len'))
    elif command==6:
        for n in ['cheap_cost','lit_len','lit_used','gap','rows']:put(n,0)
        if get('row_start')!=5664:put('group_start',get('row_start'))
    else:raise ValueError(command)
    return bytes(r)
