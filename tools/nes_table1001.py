"""Bind an admission-time HDMA table proof to exact current WRAM and SEAL fields."""
from build_nes_trace_replay import Code
from nes_dma1000 import ORIGIN

FLAG=0x7e3f80
TABLE=0x6a21
SAVED=0x3f82


def attach(writes,labels,body):
    base=ORIGIN+len(body)
    c=Code(base+len(writes[base]))
    def near(op,addr):
        c.absolute(op,addr&65535)
    def imm(v):
        c.emit(0xa9);c.word(v)
    def hook(addr,expected):
        assert body[addr-ORIGIN:addr-ORIGIN+3]==expected
        target=c.base+len(c.data)
        writes[addr]=bytes((0x4c,target&255,target>>8&255))
    def resume(addr):
        near(0x4c,addr+3)
    def require_equal(v,fail):
        c.emit(0xc9);c.word(v);c.emit(0xf0,3);c.jump(fail)
    for name,old in (("begin",bytes.fromhex("9c d8 14")),("invalidate635",bytes.fromhex("9c d0 14"))):
        addr=labels[name]
        hook(addr,old)
        c.emit(0x48);imm(0);c.long(0x8f,FLAG);c.emit(0x68)
        c.emit(*old);resume(addr)

    addr=labels["accepted"]
    hook(addr,bytes.fromhex("ad 00 12"))
    for field,value in ((0x1200,0x0502),(0x120a,1322),(0x120c,240)):
        near(0xad,field);require_equal(value,"admitted")
    imm(0);c.long(0x8f,FLAG)
    near(0xae,0x1020);c.long(0xbf,0x7f0000+TABLE+243);require_equal(21,"admitted")
    # The original grammar validates the other lengths, terminators, row
    # counts, map selection, both banks and enable/window bytes. Guessing a
    # form never grants a SEAL: on a miss the original validator runs there.
    near(0xad,0x1240);c.emit(0x48);near(0xad,0x123a);c.emit(0x48)
    imm(1);near(0x8d,0x1240);imm(0x1e);near(0x8d,0x123a)
    near(0xad,0x1020);c.emit(0x18,0x69);c.word(TABLE);c.emit(0x85,0x70)
    c.emit(0xe2,0x20,0xa9,0x7f,0x85,0x72,0xc2,0x20)
    c.emit(0xa0,0,0,0x64,0x74,0x64,0x76)
    near(0x20,labels["table181"])
    c.emit(0x68);near(0x8d,0x123a);c.emit(0x68);near(0x8d,0x1240)
    c.branch(0x90,"admitted")
    c.absolute(0x20,0)  # resolve forward assembly reference
    c.jumps.append((len(c.data)-2,"snapshot"))
    imm(1);c.long(0x8f,FLAG)
    c.label("admitted");near(0xad,0x1200);resume(addr)

    # The original scroll check, SEAL identity, compact decode and final
    # coverage still execute. Replace only the checked table loop on a hit.
    addr=labels["table181"]-7
    hook(addr,bytes.fromhex("a0 00 00"))
    c.long(0xaf,FLAG);c.branch(0xf0,"fallback")
    for field,value in ((0x1240,1),(0x123a,0x1e),(0x125e,TABLE)):
        near(0xad,field);c.emit(0xc9);c.word(value);c.branch(0xd0,"fallback")
    near(0x20,0);c.jumps.append((len(c.data)-2,"compare"))
    c.branch(0x90,"fallback")
    c.label("proof_hit");c.emit(0x38,0x60)
    c.label("fallback");c.emit(0xa0,0,0);resume(addr)
    for mode in ("snapshot","compare"):
        c.label(mode)
        c.emit(0x8b,0xf4,0x7e,0x7e,0xab,0xab)  # DBR=$7e
        near(0xae,0x1020);c.emit(0xa0,0,0);c.label(mode+"_word")
        def transfer(src,dest,indexed):
            c.long(0xbf,0x7f0000+TABLE+src)
            near((0x99 if indexed else 0x8d) if mode=="snapshot" else (0xd9 if indexed else 0xcd),SAVED+dest)
            if mode=="compare":c.branch(0xd0,"mismatch")
        for j in range(3):
            transfer(81*j,22*j,True)
        c.emit(0xe8,0xe8,0xc8,0xc8,0xc0,22,0);c.branch(0x90,mode+"_word")
        near(0xae,0x1020)
        for j in (0,2,4):transfer(243+j,66+j,False)
        c.emit(0xab,0x38,0x60)
    c.label("mismatch");c.emit(0xab,0x18,0x60)
    extra=c.finish()
    assert c.base+len(extra)<FLAG
    writes[base]+=extra
    return c.labels
