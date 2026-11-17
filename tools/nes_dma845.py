"""Queue SEAL behind checked palette credits and measure the finite 65816 group."""
import argparse
import json
from unittest.mock import patch
import nes_tail844 as prior
import nes_tile842 as base
from nes_handoff843 import CLIENT as PREACCEPTED
from nes_pair839 import Code, ORIGIN, codec, once, pack

OUT=base.section.PROBES/"nes-dma845"
BASE=prior.arm("objdone")
ARM=BASE.parent/"link-845palette"


def prepare_arm():
    name="nes_sink_window184.c"
    old=(BASE/"src"/name).read_text()
    # At SEAL, plan FINISH has already validated the last bulk. Palette
    # DATA/RLE retires in FIFO order and each physical ACK is independently
    # checked. The final drain must still verify the SEAL identity.
    s=once(old,"(p[0]!=3 || s->last[1]!=5)",
           "(p[0]!=3 || (s->last[1]!=5 && !(s->last[1]==3 && (s->last[0]==2 || s->last[0]==4))))")
    dest=OUT/"patch";dest.mkdir(parents=True,exist_ok=True)
    (dest/name).write_text(s,newline="\n")


def receiver(parent,dest,retire_raw=False):
    body=bytearray((parent/"body.bin").read_bytes())
    labels=json.loads((parent/"labels.json").read_bytes())
    c=Code(ORIGIN+len(body));c.labels.update(labels)
    # The ordinary command list and exclusive end have already passed SEAL.
    # Keep the previous cursor until the normal synchronous DMA returns.
    # Fast path retains STOP and controller service at every command boundary.
    # When X/Y are 16-bit, LDY absolute reads a word; never use it on an
    # 8-bit I/O register. Keep the MDMAEN write exactly one byte.
    c.label("normal845")
    c.emit(0x4a);c.absolute(0x8d,0x2116)
    for offset,reg in ((0,0x4302),(4,0x4305)):
        c.long(0xbf,0x7e4000+offset);c.absolute(0x8d,reg)
    c.emit(0xe2,0x20);c.store(0x420b,1)
    # CPX ($103a) is independent of M. X is updated once in 16-bit mode.
    # The group loop tests the beam only between two descriptors.
    c.emit(0xc2,0x20,0x8a,0x18,0x69,8,0,0xaa)
    c.absolute(0xec,0x103a);c.branch(0xb0,"end845")
    c.emit(0xe2,0x20);c.absolute(0xad,0x6001);c.branch(0x30,"stop845")
    c.absolute(0xad,0x4212);c.branch(0x10,"slow845")
    c.absolute(0x9c,0x1238);c.emit(0xc2,0x20)
    # A nonzero low byte excludes both compact raw addresses ($5000/$9000).
    # Carry the destination into normal845; on the rare aligned/raw path the
    # original dispatcher sees a materialized cursor.
    c.label("next845");c.long(0xbf,0x7e4002);c.emit(0x89,0xff,0)
    c.branch(0xd0,"normal845")
    c.absolute(0x8e,0x1252);c.jump("upload_loop212")
    c.label("end845");c.absolute(0x8e,0x1252);c.jump("group538")
    c.label("stop845");c.absolute(0x8e,0x1252);c.jump("seen837")
    c.label("slow845");c.absolute(0x8e,0x1252);c.jump("slow837")
    # First ordinary command uses the optimized continuation; raw commands
    # still use the existing dispatcher and advance the cursor themselves.
    i=labels["normal_dest550"]-ORIGIN
    assert body[i:i+4]==bytes.fromhex("4a8d1621")
    body[i:i+3]=bytes([0x4c])+(c.labels["normal845"]&65535).to_bytes(2,"little")
    if retire_raw:
        # prepare547 validates/records the independent committed row history.
        # Its six bits OR the actual preupload completions are precisely the
        # predicate used by raw_dma489841. Only retire the last isolated
        # descriptor with the exact two-row source, destination and charge.
        site=body.index(bytes.fromhex("201034ad3612"),labels["length635_8"]-ORIGIN)
        c.label("history845");c.absolute(0x20,labels["prepare547"]&65535)
        def require(op):
            c.branch(op,"keep845")
        def load(addr):
            c.absolute(0xad,addr)
        load(0x1236);require(0xd0)
        load(0x1240);c.emit(0xc9,2,0);require(0xd0)
        load(0x1258);c.emit(0xc9,0x80,1);require(0xd0)
        load(0x125c);c.emit(0x3a);require(0xd0)
        load(0x1506);c.emit(0x05,0x78,0xc9,63,0);require(0xd0)
        load(0x1250);c.absolute(0xcd,0x1252);require(0x90);require(0xf0)
        c.emit(0x38,0xe9,8,0,0xaa)
        load(0x1020);c.emit(0x18,0x69,0x61,0x69);c.long(0xdf,0x7e4000);require(0xd0)
        load(0x1034);c.branch(0xf0,"bank0_845")
        c.emit(0xa9,0,0x90);c.branch(0x80,"dst845")
        c.label("bank0_845");c.emit(0xa9,0,0x50)
        c.label("dst845");c.long(0xdf,0x7e4002);require(0xd0)
        c.long(0xbf,0x7e4004);c.emit(0xc9,0x60,3);require(0xd0)
        load(0x1500);c.emit(0x38,0xe9,0x60,3);require(0x90)
        c.label("drop845");c.absolute(0x8d,0x1500);c.absolute(0x8e,0x1250);c.emit(0x64,0x78)
        c.label("keep845");c.emit(0x60)
        body[site+1:site+3]=(c.labels["history845"]&65535).to_bytes(2,"little")
    body.extend(c.finish())
    used=260+len(pack(bytes(body),0))
    with patch.object(codec,"pack",pack),patch.object(codec,"STORED",max(5056,used)):
        codec.build(base.section.PROBES/"nes-reuse635/client04",dest,edit_body=lambda *_:bytes(body),
                    allow_extension=True,body_limit=8192,prefix_sizes=[0],medium_pages=True,
                    short_errors=True,boot_bytes=260,fast_backrefs=True)
    (dest/"labels.json").write_text(json.dumps(c.labels,indent=2))
    (dest/"cost.json").write_text(json.dumps(dict(ROM_bytes=used+64,capacity=5120)))


def run(mode,test,phase):
    fast=mode in ("dma","both","retire")
    with patch.object(base,"arm",lambda _: ARM if mode in ("arm","both","retire") else BASE), \
         patch.object(base,"CLIENT",OUT/("client-retire" if mode=="retire" else "client") if fast else base.CLIENT):
        base.run(mode,phase,test,tag=f"845{mode}{test}",on_attach=prior.watch)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("arm","dma","both","retire"))
    p.add_argument("test",choices=("prepare","client","fixed","stop","damage","refopening","opening","static"))
    p.add_argument("phase",type=int,nargs="?",default=1,choices=(1,2))
    a=p.parse_args()
    if a.test=="prepare":
        prepare_arm()
    elif a.test=="client":
        suffix="-retire" if a.mode=="retire" else ""
        receiver(base.CLIENT,OUT/("client"+suffix),bool(suffix))
        receiver(PREACCEPTED,OUT/("client-bg"+suffix),bool(suffix))
    else:
        run(a.mode,a.test,a.phase)
