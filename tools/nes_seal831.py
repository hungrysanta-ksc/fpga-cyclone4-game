"""MMC826 SEAL: inspect sparse requirements and three HDMA tables in bank-local order."""
import argparse
import json
from unittest.mock import patch

from build_nes_trace_replay import Code
from nes_pad647 import add_padding_history
from nes_raw506 import once, sha
from prepare_nes_map828 import PROBES, codec, pack

OUT = PROBES / "nes-seal831"
CLIENT = PROBES / "nes-output815/client"
ORIGIN = 0x7e2000


def sender(short=False,split=None):
    src=PROBES/"nes-output823/link-830joined/src/nes_native_sink165.c"
    out=OUT/("patch-splitshort" if short and split else "patch-"+split if split else "patch-short" if short else "patch")
    out.mkdir(parents=True,exist_ok=True)
    # The paired scroll/padding writes skip tile service. Recheck ownership
    # after map527, which can service a newly available bulk in the interim.
    text=once(src.read_text(),"  if(fragments>112/4){","  if(fragments>112/4 && s->plan->bulk_pending){")
    if split:
        # OAM can cross section 5 because it has its own sequential cursor.
        # The prefix/padding is already accepted for ordered issue. Leave the
        # combined palette/OAM history command on its original path.
        cond="p->objects>112/4 && p->map_dirty && !(uint32_t)r->map_upload && packed==384"
        text=once(text," bool same=same635(s,p);",f" bool bundle={cond};\n bool defer_oam=false;\n bool same=same635(s,p);")
        text=once(text," if(!oam227(s,p->oam))return false;"," defer_oam=bundle && p->scroll_issued;\n if(!defer_oam && !oam227(s,p->oam))return false;")
        text=once(text,"  if("+cond+"){","  if(bundle){")
        after="    if(!packet(s,2,5,offset+pos,bundle+pos,n))return false;"
        text=once(text,after,after+"\n    if(pos=="+("0" if split=="split" else "480")+" && defer_oam && !oam227(s,p->oam))return false;")
    if short:
        if split:
            text=once(text,"memcpy(bundle+384,p->patch.mode,162);\n   memcpy(bundle+546,p->patch.enable,81);",
                      "memcpy(bundle+384,(const uint8_t *)p+__builtin_offsetof(struct nes_native_video165,patch.mode),243);")
            text=once(text,"for(unsigned bit=0;bit<2;bit++)out[packed++]=p->patch.chr[tile*64+plane*16+row*2+bit];",
                      "{memcpy(out+packed,p->patch.chr+tile*64+plane*16+row*2,2);packed+=2;}")
        text=once(text," memcpy(descriptor+24,r->used,144);\n if(!packet(s,3,0,0,descriptor,sizeof descriptor))", """ unsigned length=168;
 if(p->obj_count>=64){
  unsigned i=16;
  while(i<128 && !r->used[i])i++;
  if(i==128)length=56;
 }
 memcpy(descriptor+24,r->used,length-24);
 if(length==56)memcpy(descriptor+40,r->used+128,16);
 if(!packet(s,3,0,0,descriptor,length))""")
    (out/src.name).write_text(text,newline="\n")


def checked_tables(c):
    # The pointer supplied by scroll_end181 addresses a bounded table in
    # bank 7F. X is the current absolute offset, Y the relative terminator
    # position expected by the original length/sum checks.
    c.emit(0xa6,0x70)
    c.label("row831")
    def sample(offset):
        c.long(0xbf,0x7f0000+offset)
    def check(op):
        c.emit(op^0x20,3); c.jump("invalid181")
    sample(0); c.emit(0x29,255,0)
    c.emit(0xd0,3); c.jump("table_end181")
    c.emit(0xc9,128,0); check(0xb0)
    c.emit(0x85,0x78,0x18,0x65,0x74,0x85,0x74,0xc9,225,0); check(0xb0)
    for off in (81,162):
        sample(off); c.emit(0x29,255,0,0xc5,0x78); check(0xd0)
    sample(1); c.emit(0xc9,3,0); c.branch(0xf0,"raw831")
    c.emit(0xc9,0,0); check(0xd0)
    c.emit(0xa9,0x31,0,0x85,0x7a,0xa9,0x11,0,0x85,0x7c)
    c.absolute(0xad,0x123a); c.emit(0xc9,0x18,0)
    c.branch(0xf0,"clip831"); c.emit(0xa9,0,0); c.branch(0x80,"window831")
    c.label("clip831"); c.emit(0xa9,17,0)
    c.label("window831"); c.emit(0x85,0x7e); c.branch(0x80,"values831")
    c.label("raw831"); c.emit(0xa5,0x76,0x18,0x65,0x78,0x85,0x76)
    c.emit(0xa9,0x38,0,0x85,0x7a,0xa9,1,0,0x85,0x7c,0x64,0x7e)
    c.label("values831")
    sample(1); c.long(0xdf,0x7f0052); check(0xd0)
    for off,zp in ((3,0x7a),(84,0x7a),(163,0x7c),(165,0x7e)):
        sample(off)
        if off==84:
            c.emit(0x38,0xe9,0x20,0)
        c.emit(0xc5,zp); check(0xd0)
    c.emit(0x8a,0x18,0x69,5,0,0xaa,0x98,0x18,0x69,5,0,0xa8,0xc0,81,0)
    check(0xb0); c.jump("row831")


def client(fast_tail=False, padding=False, short=False):
    assert sha(CLIENT/"sink165.sfc") == "3ca9aaefd9efad64a3cb63b59b627314f9f6b8e87fb79e236ba7e7d01fa856e1"
    body = bytearray((CLIENT/"body.bin").read_bytes())
    labels = json.loads((CLIENT/"labels.json").read_bytes())

    def block(first, end, emit):
        lo, hi = labels[first], labels[end]
        c = Code(lo)
        c.labels.update(labels)
        emit(c)
        code = c.finish()
        assert len(code) <= hi-lo, (first, len(code), hi-lo)
        body[lo-ORIGIN:hi-ORIGIN] = code + bytes(hi-lo-len(code))
        labels.update(c.labels)

    def requirements(c):
        # Read every required word from the SEAL head. A zero word has no
        # dependencies. Every set bit must be independently present in WRAM.
        c.emit(0xa2,0,0); c.absolute(0xac,0x1254)
        c.label("loop831")
        for off in range(0,8,2):
            c.long(0xbf,0x400028+off)
            c.branch(0xf0,"next831_"+str(off))
            c.emit(0x49,255,255); c.absolute(0x19,0x1320+off)
            c.emit(0x1a); c.branch(0xd0,"missing831")
            c.label("next831_"+str(off))
        for seq in ((0x98,0xa8),(0x8a,0xaa)):
            c.emit(seq[0],0x18,0x69,8,0,seq[1])
        c.emit(0xe0,144,0); c.branch(0xd0,"loop831")
        c.jump("covered619")
        c.label("missing831"); c.jump("mark_bad212")

    block("coverage212","covered619",requirements)
    block("table181","table_end181",checked_tables)
    if fast_tail:
        # DATA8 has already validated its 4-byte period, inactive OAM bounds
        # and alignment. DATA4/5 have already validated their 2-byte period.
        # Keep the fixed-byte DMA path for uniform runs. Other runs below
        # use the same source bytes and poll STOP at least every 64 bytes.
        c=Code(ORIGIN+len(body))
        c.labels.update(labels)
        def gate(addr,old,name):
            i=addr-ORIGIN
            assert body[i:i+len(old)]==old
            c.label(name)
            body[i:i+3]=bytes((0x4c,))+ (c.labels[name]&65535).to_bytes(2,"little")
        repeat4=body.index(bytes.fromhex("8ba67aa57a18690400a8"),labels["literal_length227"]-ORIGIN)
        gate(ORIGIN+repeat4,bytes.fromhex("8ba67a"),"repeat4_831")
        c.emit(0xa6,0x7a); c.absolute(0xac,0x120c)
        # Rewrite the first four literal bytes as part of the same pattern.
        # Y counts the remaining bytes and X the bank-local destination.
        for period in (4,2):
            if period==2:
                gate(labels["word516"],bytes.fromhex("ac0c12"),"repeat2_831")
                c.emit(0xc2,0x20,0xa6,0x7a); c.absolute(0xac,0x120c)
            c.label(f"chunk831_{period}")
            c.emit(0xc0,64,0,0xb0,3); c.jump(f"tail831_{period}")
            for pos in range(0,period,2):
                c.long(0xaf,0x400010+pos)
                for off in range(pos,64,period):
                    c.long(0x9f,0x7f0000+off)
            c.emit(0x8a,0x18,0x69,64,0,0xaa,0x98,0x38,0xe9,64,0,0xa8)
            c.absolute(0x20,labels["service"]&65535)
            c.branch(0xf0,f"more831_{period}"); c.jump("stop_packet")
            c.label(f"more831_{period}"); c.jump(f"chunk831_{period}")
            c.label(f"tail831_{period}"); c.emit(0xc0,0,0); c.branch(0xf0,f"end831_{period}")
            for pos in range(0,period,2):
                c.long(0xaf,0x400010+pos); c.long(0x9f,0x7f0000+pos)
            c.emit(0x8a,0x18,0x69,period,0,0xaa,0x98,0x38,0xe9,period,0,0xa8)
            c.branch(0xd0,f"tail831_{period}")
            c.label(f"end831_{period}"); c.jump("repeat_done1815")
        body.extend(c.finish())
        labels=c.labels
    if padding:
        body,labels=add_padding_history(body,labels)
    if short:
        body=bytearray(body)
        c=Code(ORIGIN+len(body))
        c.labels.update(labels)
        def entry(address,old,label):
            i=address-ORIGIN
            assert body[i:i+len(old)]==old
            c.label(label)
            body[i:i+3]=bytes((0x4c,))+(c.labels[label]&65535).to_bytes(2,"little")
        width=body.index(bytes.fromhex("c9a800f003"),labels["seal"]-ORIGIN)
        entry(ORIGIN+width,bytes.fromhex("c9a800"),"width831")
        c.emit(0xc9,56,0); c.branch(0xf0,"size_ok831"); c.emit(0xc9,168,0)
        c.branch(0xf0,"size_ok831"); c.jump("bad_packet")
        c.label("size_ok831"); c.absolute(0x4c,(ORIGIN+width+8)&65535)
        entry(labels["coverage212"],bytes.fromhex("a20000"),"extent831")
        c.absolute(0xad,0x120c); c.emit(0xc9,56,0)
        c.branch(0xf0,"short831")
        c.emit(0xa2,0,0); c.absolute(0x4c,(labels["coverage212"]+3)&65535)
        c.label("short831"); c.emit(0xa2,0,0); c.absolute(0xac,0x1254)
        c.label("word831"); c.absolute(0xb9,0x1320); c.emit(0x49,255,255)
        c.long(0x3f,0x400028); c.branch(0xf0,"good831"); c.jump("mark_bad212")
        c.label("good831"); c.emit(0xe8,0xe8,0xc8,0xc8,0xe0,16,0)
        c.branch(0xd0,"end_extent831"); c.emit(0x98,0x18,0x69,112,0,0xa8)
        c.label("end_extent831"); c.emit(0xe0,32,0); c.branch(0xd0,"word831")
        c.emit(0xa2,144,0); c.jump("covered619")
        body.extend(c.finish()); labels=c.labels
    out=OUT/("client-short" if short and padding else "client-wire" if short else "client-pad" if padding else "client-tail" if fast_tail else "client")
    with patch.object(codec,"pack",pack):
        codec.build(PROBES/"nes-reuse635/client04",out,edit_body=lambda *_:bytes(body),
                    allow_extension=True,prefix_sizes=[128,64,16,2],medium_pages=True,
                    boot_bytes=320,fast_backrefs=True)
    (out/"labels.json").write_text(json.dumps(labels,indent=2)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--tail",action="store_true")
    mode.add_argument("--pad",action="store_true")
    mode.add_argument("--short",action="store_true")
    mode.add_argument("--wire",action="store_true")
    mode.add_argument("--sender",choices=("split","lateoam","splitshort"))
    args=parser.parse_args()
    if args.sender:
        sender(short=args.sender=="splitshort",split="split" if args.sender=="splitshort" else args.sender)
    else:
        client(args.tail,args.pad or args.short,args.short or args.wire)
        sender(args.short or args.wire)
