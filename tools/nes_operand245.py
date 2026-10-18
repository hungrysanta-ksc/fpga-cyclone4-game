# SPDX-License-Identifier: MIT
"""Row hot path plus shared shift/raster/cheap record routines, not full encoder."""
from nes_operand244 import assemble as assemble244, LAYOUT, OPS as OPS244

OPS={**OPS244, 'ROWPAIR':27, 'ROWRESULT':28, 'ROWSCALE':29}


def assemble():
    words,entries=assemble244();labels={};fix=[]
    def emit(op,v=0):
        if isinstance(v,str):fix.append((len(words),v));v=0
        assert 0<=v<8192;words.append((OPS[op]<<13)|v)
    def rf(op,n,i=0):emit(op,LAYOUT[n][i]-96)
    def label(n):assert n not in labels;labels[n]=len(words)
    def begin(n):entries[n]=len(words)
    def ret(v):emit('LDI',v);emit('HALT')
    begin('row_compare');emit('ROWPAIR',0);emit('HALT')
    begin('mask_compare');emit('ROWPAIR',1);emit('CMPI',0);emit('JZ','mask_result')
    rf('LD','rows');emit('CMPI',0);emit('JZ','mask_result');emit('ADDI',1);rf('ST','rows')
    label('mask_result');emit('LDTEMP');rf('ST','xor_byte');emit('ROWRESULT');emit('HALT')
    begin('mask_set');emit('ROWPAIR',2);emit('LDTEMP');rf('ST','xor_byte');emit('LDI',1);rf('ST','rows');emit('ROWRESULT');emit('HALT')
    begin('row_more');rf('LD','rows');emit('ADDI',1);rf('ST','rows');ret(0)
    # Shift direction arg0.low is +1 (left) or255 (right), from row_compare.
    # Emit N[64:66] or N[0:2], never a copy into another payload RAM.
    begin('shift');emit('LDI',7);emit('RECORD')
    rf('LD','row_start');emit('OUT');rf('LD','row_start',1);emit('OUT')
    emit('LDI',0);emit('OUT');emit('LDI',2);emit('OUT');emit('ARG',0);emit('OUT')
    emit('CMPI',1);emit('JZ','left');emit('LDI',128);emit('JMP','edge')
    label('left');emit('LDI',192)
    label('edge');emit('ADDR',0);emit('LDP');emit('OUT');emit('INCADDR');emit('LDP');emit('OUT')
    rf('LD','expanded');emit('ADDI',66);rf('ST','expanded');rf('LD','expanded',1);emit('ADCI',0);rf('ST','expanded',1);emit('JMP','span')
    begin('raster');emit('LDI',13);emit('RECORD')
    rf('LD','group_start');emit('OUT');rf('LD','group_start',1);emit('OUT')
    emit('LDI',0);emit('OUT');emit('LDI',1);emit('OUT');rf('LD','rows');emit('OUT')
    emit('LDI',96);emit('ADDR',0)
    label('mask_send');emit('LDP');emit('OUT');emit('INCADDR');emit('GETADDR');emit('CMPI',104);emit('JZ','mask_sent');emit('JMP','mask_send')
    label('mask_sent');rf('LD','rows');emit('ROWSCALE',0);rf('ADD','expanded');rf('ST','expanded')
    rf('LD','rows');emit('ROWSCALE',1);rf('ADC','expanded',1);rf('ST','expanded',1);emit('JMP','span')
    # Cheap group consists of complete records previously produced by FLUSH.
    # Reject malformed length/total before that record's publication, although
    # callers can only construct these bytes through the checked FLUSH routine.
    begin('cheap');rf('LD','cheap_cost');emit('CMPI',13);emit('JC','bad_cheap');emit('LDI',0);rf('ST','cheap_i')
    label('cheap_next');rf('LD','cheap_i');rf('CMP','cheap_cost');emit('JZ','cheap_done')
    rf('LD','cheap_i');emit('ADDI',82);emit('ADDR',0);emit('LDP');emit('ADDI',3);emit('TEMP')
    emit('CMPI',4);emit('JC','cheap_size');emit('FAIL')
    label('cheap_size');emit('CMPI',13);emit('JC','bad_cheap')
    rf('ADD','cheap_i');rf('CMP','cheap_cost');emit('JZ','cheap_ok');emit('JC','bad_cheap')
    label('cheap_ok');emit('LDTEMP');rf('ST','build_i');emit('RECORD')
    rf('LD','cheap_i');emit('ADDI',80);emit('ADDR',0)
    label('cheap_send');emit('LDP');emit('OUT');emit('INCADDR')
    rf('LD','cheap_i');emit('ADDI',1);rf('ST','cheap_i')
    emit('LDTEMP');emit('ADDI',255);emit('TEMP');emit('CMPI',0);emit('JZ','cheap_count');emit('JMP','cheap_send')
    # build_i is dead after cheap FLUSH copies; reuse it for length, no new FF.
    label('cheap_count');rf('LD','build_i');emit('ADDI',253);rf('ADD','expanded');rf('ST','expanded')
    rf('LD','expanded',1);emit('ADCI',0);rf('ST','expanded',1)
    rf('LD','spans');emit('ADDI',1);rf('ST','spans');rf('LD','spans',1);emit('ADCI',0);rf('ST','spans',1);emit('JMP','cheap_next')
    label('bad_cheap');emit('FAIL')
    label('cheap_done');ret(0)
    label('span');rf('LD','spans');emit('ADDI',1);rf('ST','spans');rf('LD','spans',1);emit('ADCI',0);rf('ST','spans',1);ret(0)
    for i,n in fix:words[i]|=labels[n]
    assert len(words)<=512,len(words)
    return words,entries
