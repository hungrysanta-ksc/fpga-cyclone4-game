"""Copy the packed client into WRAM and replay the encoded stream to verify every byte."""
import json
from build_nes_trace_replay import Code
from nes_native_local165 import call
from pack_nes_column854 import encode,decode

DEST=0x2000
STORED=5056


def build(base,out,body,labels,straight=False):
    stored=bytearray(body)
    if straight:
        tail=labels['suffix']-0x7e0000
        pattern=b''.join(bytes((0x19,i*2,0)) for i in range(1,32))
        assert stored[tail-DEST:tail-DEST+93]==pattern
        stored[tail-DEST:tail-DEST+93]=bytes(93)
    rom=(base/'sink165.sfc').read_bytes()
    def loader(prefix,first,limit):
        c=Code(0x8000)
        def imm(op,v):c.emit(op);c.word(v)
        # Retain the previous boot status, stack, interrupt and PPU setup.
        end_init=rom.index(bytes.fromhex('8d 00 70 c2 30'))+3; c.emit(*rom[:end_init])
        c.emit(0xc2,0x30)
        if prefix==0:
            c.emit(0xf4,0x7e,0x7e,0xab,0xab)
        else:
            imm(0xa9,prefix-1);imm(0xa2,first);imm(0xa0,DEST);c.emit(0x54,0x7e,0)
            imm(0xa2,0);c.label('prefix');c.long(0xbf,first);c.long(0xdf,0x7e0000+DEST)
            c.emit(0xf0,3);c.jump('bad')
            c.emit(0xe8,0xe8);imm(0xe0,prefix);c.branch(0xd0,'prefix')
        c.emit(0xe2,0x20,0x64,2)
        c.label('pass');imm(0xa2,first+prefix);imm(0xa0,DEST+prefix);c.emit(0x64,3)
        c.label('token');imm(0xc0,DEST+len(body));c.branch(0xf0,'end')
        # The sentinel in bit 7 survives exactly seven subsequent shifts.
        c.emit(0x46,3);c.branch(0xd0,'flag');call(c,'read')
        c.emit(0x38,0x6a,0x85,3)
        c.label('flag');c.branch(0xb0,'match')
        call(c,'read');c.emit(0x24,2);c.branch(0x30,'literal_check')
        c.absolute(0x99,0);c.branch(0x80,'literal_done')
        c.label('literal_check');c.absolute(0xd9,0);c.branch(0xd0,'bad')
        c.label('literal_done');c.emit(0xc8);c.branch(0x80,'token')
        c.label('match');call(c,'read');c.emit(0x85,4);call(c,'read')
        c.emit(0x48,0x4a,0x4a,0x4a,0x4a,0x85,5,0x68,0x29,15,0x18,0x69,3,0x85,6,0x64,7)
        c.emit(0xc2,0x20,0x98,0x18,0x65,6);imm(0xc9,DEST+len(body)+1);c.branch(0xb0,'bad')
        c.emit(0x98,0x18,0xe5,4);imm(0xc9,DEST);c.branch(0x90,'bad')
        c.emit(0xda,0xaa,0xa5,6,0x3a,0x24,2); # BIT $02 in 16-bit sees flag byte too; use 8-bit phase test.
        c.emit(0xe2,0x20,0x24,2);c.branch(0x30,'verify')
        c.emit(0xc2,0x20,0x54,0x7e,0x7e,0xe2,0x20);c.branch(0x80,'match_done')
        c.label('verify');c.absolute(0xbd,0);c.label('compare');c.absolute(0xd9,0);c.branch(0xd0,'bad')
        c.emit(0xe8,0xc8,0xc6,6);c.branch(0xd0,'verify')
        c.label('match_done');c.emit(0xfa);c.jump('token')
        c.label('end');imm(0xe0,limit);c.branch(0xd0,'bad')
        c.emit(0xa5,2);c.branch(0x30,'ready');c.emit(0xa9,128,0x85,2);c.jump('pass')
        c.label('ready')
        if straight:call(c,'expand_suffix')
        c.emit(0xa9,0,0x48,0xab);c.long(0x5c,0x7e2000)
        c.label('read');imm(0xe0,limit);c.branch(0xb0,'bad');c.long(0xbf,0);c.emit(0xe8,0x60)
        c.label('bad');c.emit(0xe2,0x20,0xa9,0xe1);c.long(0x8f,0x007000);c.emit(0x80,0xfe)
        if straight:
            # The verified stream supplies all 31 zero high operand bytes.
            # Check each generated opcode and displacement before entry.
            c.label('expand_suffix');c.emit(0xc2,0x20);imm(0xa2,tail);imm(0xa9,0x0219)
            c.label('expand_word');c.absolute(0x9d,0);c.absolute(0xdd,0);c.branch(0xd0,'bad')
            c.emit(0x18);imm(0x69,0x200);c.emit(0xe8,0xe8,0xe8);imm(0xe0,tail+93)
            c.branch(0xd0,'expand_word');c.emit(0xe2,0x20,0x60)
        return c.finish(),c.labels
    for prefix in range(1024,-1,-32):
        stub,_=loader(prefix,0x8100,0x9000)
        first=0x8000+len(stub)
        stream=encode(bytes(stored),prefix)
        if len(stub)+len(stream)<=STORED:break
    else:raise ValueError('physical ROM capacity')
    assert decode(stream,prefix,len(body))==stored
    limit=first+len(stream)
    code,boot=loader(prefix,first,limit)
    assert len(code)==len(stub)
    result=bytearray([255])*32768
    result[:len(code)]=code;result[len(code):limit-0x8000]=stream
    result[-64:]=rom[-64:]
    out.mkdir(parents=True)
    (out/'body.bin').write_bytes(body)
    (out/'sink165.sfc').write_bytes(result)
    (out/'sink-program.hex').write_text(''.join(f'{b:02x}\n' for b in result[:STORED]+result[-64:]),newline='\n')
    (out/'labels.json').write_text(json.dumps(labels)+'\n')
    info=json.loads((base/'build.json').read_bytes())
    info.update(candidate='column854',body_bytes=len(body),copy_verified_bytes=len(body),loader_B=len(code),
                encoded_B=len(stream)-prefix,prefix_B=prefix,physical_free_B=STORED-len(code)-len(stream),
                verify_entry=boot['compare'],boot_error=boot['bad'])
    (out/'build.json').write_text(json.dumps(info,indent=2)+'\n')
