"""MMC826 section 5. Five little-endian words expand to 128+4*64 bytes."""
import argparse
import json
from unittest.mock import patch

from build_nes_trace_replay import Code
from nes_raw506 import once, sha
from nes_report828 import reports
from prepare_nes_map828 import PROBES, codec, pack
from prepare_nes_section832 import BASE, prepare as prepare832
from link_nes_section832 import build as overlay

OUT=PROBES/"nes-repeat833"


def sender(mode):
    src=BASE/"src"
    out=OUT/("patch-"+mode)
    out.mkdir(exist_ok=True,parents=True)
    reports(src,out)
    name="nes_native_sink165.c"
    text=(src/name).read_text()
    old="if(!span(s,5,offset,raw,packed))return false;"
    if mode=="early":
        prepare832("rleburst")
        text=(PROBES/"nes-section832/patch-rleburst"/name).read_text()
        old="if(!span(s,5,1121,bundle,384))return false;"
    helper="""static bool raw833(struct nes_native_sink165 *s,const uint8_t *raw,unsigned size){
 if(size==384){
  uint8_t words[10];
  unsigned pos=0;
  for(unsigned i=0;i<5;i++){
   unsigned n=i?64:128;
   if(memcmp(raw+pos,raw+pos+2,n-2))break;
   memcpy(words+2*i,raw+pos,2);pos+=n;
  }
  if(pos==384)return packet(s,9,5,1121,words,sizeof words);
 }
 return span(s,5,1121,raw,size);
}
"""
    text=once(text,"bool nes_sink212_seal(",helper+"bool nes_sink212_seal(")
    text=once(text,old,"if(!raw833(s,"+("bundle,384" if mode=="early" else "raw,packed")+"))return false;")
    if mode in ("mid","first"):
        begin=text.index(" if(!p->scroll_issued && !span(s,5")
        end=text.index(" uint8_t descriptor[168];",begin)
        block=text[begin:end].replace("size[5]=(uint16_t)","*size=(uint16_t)")
        text=text[:begin]+" if(!issued && !section833(s,p,raw,packed,size+5))return false;\n"+text[end:]
        decl="static bool section833(struct nes_native_sink165 *s,struct nes_native_video165 *p,const uint8_t *raw,unsigned packed,uint16_t *size){\n"
        text=once(text,"bool nes_sink212_seal(",decl+block+" return true;\n}\nbool nes_sink212_seal(")
        text=once(text," bool same=same635(s,p);"," bool issued=false;\n bool same=same635(s,p);")
        anchor=" if(!span(s,3,0,p->cgram,512))return false;"
        prefix=128 if mode=="mid" else 0
        text=once(text,anchor,""" if(packed==384 && p->objects>28 && p->map_dirty && !(uint32_t)r->map_upload &&
    s->plan && s->plan->bank_history==2){
"""+("  if(!span(s,3,0,p->cgram,128))return false;\n" if prefix else "")+
            f"  if(!section833(s,p,raw,packed,size+5) || !span(s,3,{prefix},p->cgram+{prefix},{512-prefix}))return false;\n"+
            "  issued=true;\n }else"+anchor)
    if mode in ("oam","front"):
        begin=text.index(" if(!p->scroll_issued && !span(s,5")
        end=text.index("  offset+=packed;",begin)
        block=text[begin:end]
        text=text[:begin]+" if(!issued && !prefix833(s,p,raw,packed))return false;\n if(p->patch_count){\n  unsigned offset=1121;\n"+text[end:]
        decl="static bool prefix833(struct nes_native_sink165 *s,struct nes_native_video165 *p,const uint8_t *raw,unsigned packed){\n"
        text=once(text,"bool nes_sink212_seal(",decl+block+" }\n return true;\n}\nbool nes_sink212_seal(")
        text=once(text," bool same=same635(s,p);"," bool issued=false;\n bool same=same635(s,p);")
        anchor=" if(!oam227(s,p->oam))return false;" if mode=="oam" else " if(!span(s,3,0,p->cgram,512))return false;"
        text=once(text,anchor,""" if(packed==384 && p->objects>28 && p->map_dirty && !(uint32_t)r->map_upload &&
    s->plan && s->plan->bank_history==2){
  if(!prefix833(s,p,raw,packed))return false;
  issued=true;
 }
"""+anchor)
    (out/name).write_text(text,newline="\n")


def client(src=None,out=None,*,expected="3ca9aaefd9efad64a3cb63b59b627314f9f6b8e87fb79e236ba7e7d01fa856e1",step=8,inspect_first=False,repair_step=None):
    src=src or PROBES/"nes-output815/client"
    assert sha(src/"sink165.sfc")==expected and step in (8,16)
    body=bytearray((src/"body.bin").read_bytes())
    c=Code(0x7e2000+len(body))
    c.labels.update(json.loads((src/"labels.json").read_bytes()))
    def gate(pc,old,name):
        c.label(name)
        i=pc-0x2000
        assert body[i:i+3]==bytes.fromhex(old)
        body[i:i+3]=bytes([0x4c])+(c.labels[name]&65535).to_bytes(2,"little")
    gate(0x224c,"4c d4 34","header833")
    c.absolute(0xad,0x1200);c.emit(0xc9,9,5);c.branch(0xf0,"bundle833");c.jump("reuse635")
    c.label("bundle833")
    for address,word in ((0x120a,1121),(0x120c,10),(0x120e,0)):
        c.absolute(0xad,address);c.emit(0xc9);c.word(word);c.branch(0xd0,"reject833")
    c.emit(0xa9,0x80,1);c.absolute(0x8d,0x120c);c.jump("data")
    c.label("reject833");c.jump("bad_packet")
    gate(0x252f,"4c db 25","value833")
    c.emit(0xc9,9);c.branch(0xd0,"ordinary833")
    c.emit(0xe0,10,0);c.branch(0xf0,"expand833")
    c.label("ordinary833");c.jump("literal1814")
    c.label("expand833");c.emit(0xc2,0x20,0x64,0x60)
    c.label("row833");c.emit(0xa6,0x60);c.branch(0xf0,"word833");c.emit(0xca,0xca)
    c.label("word833");c.long(0xbf,0x400010);c.emit(0x85,0x62,0xa6,0x7a,0xa0,64//step,0)
    if inspect_first:
        # Check the physical destination, even on the first use of a bank.
        # A miss starts a full write followed by a separate readback.
        c.label("inspect834")
        for off in range(0,step,2):
            c.long(0xdf,0x7f0000+off);c.branch(0xd0,"repair834")
        c.emit(0x8a,0x18,0x69,step,0,0xaa,0xa5,0x62,0x88)
        c.branch(0xd0,"inspect834");c.jump("verified834")
        if repair_step is not None:
            assert repair_step in (2,4,8,16)
            step=repair_step
        c.label("repair834");c.emit(0xa6,0x7a,0xa0,64//step,0)
    c.label("store833")
    for off in range(0,step,2):c.long(0x9f,0x7f0000+off)
    c.emit(0x8a,0x18,0x69,step,0,0xaa,0xa5,0x62,0x88);c.branch(0xd0,"store833")
    c.emit(0xa6,0x7a,0xa0,64//step,0)
    c.label("check833")
    for off in range(0,step,2):
        c.long(0xdf,0x7f0000+off);c.branch(0xd0,"damage833")
    c.emit(0x8a,0x18,0x69,step,0,0xaa,0xa5,0x62,0x88);c.branch(0xd0,"check833")
    c.label("verified834");c.emit(0x86,0x7a,0xeb,0xc5,0x62);c.branch(0xd0,"service833")
    # Existing pending record uses byte+1 for an independently verified
    # uniform row; the ordinary BEGIN/fault/final ACK own its lifetime.
    c.emit(0x29,255,0,0x1a,0xa6,0x60);c.absolute(0x9d,0x14a0)
    c.label("service833");c.absolute(0x20,c.labels["service"]&65535)
    c.branch(0xf0,"next833");c.jump("stop_packet")
    c.label("damage833");c.jump("bad_packet")
    c.label("next833");c.emit(0xe6,0x60,0xe6,0x60,0xa5,0x60,0xc9,12,0)
    c.branch(0xf0,"done833");c.jump("row833")
    c.label("done833");c.jump("accepted")
    body.extend(c.finish())
    out=out or OUT/"client"
    with patch.object(codec,"pack",pack):
        codec.build(PROBES/"nes-reuse635/client04",out,edit_body=lambda *_:bytes(body),
                    allow_extension=True,prefix_sizes=[128,64,16,2],medium_pages=True,boot_bytes=320,fast_backrefs=True)
    (out/"labels.json").write_text(json.dumps(c.labels,indent=2)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("stock","early","mid","first","oam","front","client"))
    p.add_argument("--overlay",action="store_true")
    a=p.parse_args()
    if a.overlay:
        overlay(a.mode,PROBES/"nes-output823"/("link-833"+a.mode),OUT)
    elif a.mode=="client":client()
    else:sender(a.mode)
