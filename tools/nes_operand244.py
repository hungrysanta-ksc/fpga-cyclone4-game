# SPDX-License-Identifier: MIT
"""Literal lifecycle on the shared byte engine; outer240 controller still unbound."""
from nes_operand243 import assemble as assemble243, LAYOUT, OPS as OPS243

OPS={**OPS243,**dict(CMPI=17,CMPARG=18,ADDR=19,LDP=20,STP=21,INCADDR=22,
                   TEMP=23,LDTEMP=24,GETADDR=25,RECORD=26)}

def assemble():
    words,entries=assemble243();labels={};fix=[]
    def emit(op,v=0):
        if isinstance(v,str):fix.append((len(words),v));v=0
        assert 0<=v<8192;words.append((OPS[op]<<13)|v)
    def rf(op,n,i=0):emit(op,LAYOUT[n][i]-96)
    def label(n):assert n not in labels;labels[n]=len(words)
    def begin(n):entries[n]=len(words)
    def ret(v):emit('LDI',v);emit('HALT')
    def clear(names):
        emit('LDI',0)
        for n in names:rf('ST',n)
    def copy(a,b):
        for i in range(len(LAYOUT[a])):rf('LD',a,i);rf('ST',b,i)
    # byte_at/old_byte come from row_byte/direct context, arg0.low is new byte,
    # arg1.bit0 raster, bit1 raw. Result0 consumed,1 expensive,2 flush/retry,
    # 3 flush/advance. A held input must not be accepted twice on result2.
    begin('literal')
    emit('ARG',0);rf('CMP','old_byte');emit('JZ','same')
    rf('LD','lit_len');emit('CMPI',240);emit('JZ','retry');emit('JMP','append')
    label('same');rf('LD','lit_len');emit('CMPI',0);emit('JZ','consumed')
    emit('CMPI',240);emit('JZ','after');rf('LD','gap');emit('CMPI',3);emit('JZ','after')
    label('append');entries['append']=len(words)
    rf('LD','lit_len');emit('CMPI',0);emit('JZ','at');emit('JMP','write')
    label('at');copy('byte_at','lit_at')
    label('write');rf('LD','lit_len');emit('ADDR',1);emit('ARG',0);emit('STP')
    rf('LD','lit_len');emit('ADDI',1);rf('ST','lit_len')
    emit('ARG',0);rf('CMP','old_byte');emit('JZ','gap')
    rf('LD','lit_len');rf('ST','lit_used');clear(['gap'])
    emit('ARG',2);emit('ANDI',1);emit('CMPI',0);emit('JZ','consumed')
    rf('LD','cheap_cost');emit('ADDI',3);rf('ADD','lit_len');emit('JC','expensive');emit('CMPI',13);emit('JC','expensive');emit('JMP','consumed')
    label('gap');rf('LD','gap');emit('ADDI',1);emit('ANDI',7);rf('ST','gap')
    label('consumed');ret(0)
    label('retry');ret(2)
    label('after');ret(3)
    label('expensive');clear(['cheap_cost','lit_len','lit_used','gap']);ret(1)
    # FLUSH runs header/copy/LDONE or complete literal record publication.
    # A normal record is announced before its first byte. Counts commit only
    # after all bytes have been queued; outer frame/display ACK is separate.
    begin('flush');rf('LD','lit_used');emit('CMPI',0);emit('JZ','empty')
    emit('ARG',2);emit('ANDI',1);emit('CMPI',0);emit('JZ','normal')
    rf('LD','cheap_cost');emit('ADDI',3);rf('ADD','lit_used');emit('JC','expensive');emit('CMPI',13);emit('JC','expensive')
    rf('LD','cheap_cost');emit('ADDI',80);emit('ADDR',0)
    rf('LD','lit_at');emit('STP');emit('INCADDR');rf('LD','lit_at',1);emit('STP');emit('INCADDR');rf('LD','lit_used');emit('STP')
    clear(['build_i'])
    label('copy');rf('LD','build_i');emit('ADDR',1);emit('LDP');emit('TEMP')
    rf('LD','cheap_cost');emit('ADDI',83);rf('ADD','build_i');emit('ADDR',0);emit('LDTEMP');emit('STP')
    rf('LD','build_i');emit('ADDI',1);rf('CMP','lit_used');emit('JZ','copied');rf('ST','build_i');emit('JMP','copy')
    label('copied');rf('LD','cheap_cost');emit('ADDI',3);rf('ADD','lit_used');emit('ANDI',15);rf('ST','cheap_cost');emit('JMP','cleared')
    label('normal');rf('LD','lit_used');emit('ADDI',3);emit('RECORD')
    rf('LD','lit_at');emit('OUT');rf('LD','lit_at',1);emit('OUT');rf('LD','lit_used');emit('OUT')
    emit('LDI',0);emit('ADDR',1)
    label('send');emit('LDP');emit('OUT');emit('INCADDR');emit('GETADDR');rf('CMP','lit_used');emit('JZ','sent');emit('JMP','send')
    label('sent');emit('ARG',2);emit('ANDI',2);emit('CMPI',0);emit('JZ','geometry');emit('JMP','cleared')
    label('geometry');rf('LD','spans');emit('ADDI',1);rf('ST','spans');rf('LD','spans',1);emit('ADCI',0);rf('ST','spans',1)
    rf('LD','expanded');rf('ADD','lit_used');rf('ST','expanded');rf('LD','expanded',1);emit('ADCI',0);rf('ST','expanded',1)
    label('cleared');clear(['lit_len','lit_used','gap']);ret(0)
    label('empty');clear(['lit_len','gap']);ret(0)
    # Cold/raw append accepts byte payload regardless of old value.
    begin('raw_append');rf('LD','lit_len');emit('ADDR',1);emit('ARG',0);emit('STP')
    rf('LD','lit_len');emit('ADDI',1);rf('ST','lit_len');rf('ST','lit_used');ret(0)
    # A direct literal context replaces the dead FSTORE writes only when used.
    begin('context');emit('ARG',0);rf('ST','byte_at');emit('ARG',1);emit('ANDI',31);rf('ST','byte_at',1)
    emit('ARG',2);rf('ST','old_byte');ret(0)
    begin('literal_at');emit('ARG',0);rf('ST','lit_at');emit('ARG',1);emit('ANDI',31);rf('ST','lit_at',1);ret(0)
    # Port/negative fixtures, not codec entry points.
    begin('port_store');emit('ARG',0);emit('ADDR',1);emit('ARG',2);emit('STP');ret(0)
    begin('port_read');emit('ARG',0);emit('ADDR',1);emit('LDP');emit('OUT');ret(0)
    begin('bad_payload');emit('LDI',104);emit('ADDR',0);emit('LDI',99);emit('STP');emit('HALT')
    begin('bad_wrap');emit('LDI',255);emit('ADDR',1);emit('INCADDR');emit('HALT')
    for i,n in fix:words[i]|=labels[n]
    assert len(words)<=512,len(words)
    return words,entries
