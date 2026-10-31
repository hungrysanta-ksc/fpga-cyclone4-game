# SPDX-License-Identifier: MIT
"""Build the two independent MMC509 transfer changes."""
import argparse
from pathlib import Path

import nes_output489
from nes_raw506 import encode, once

MAP_ENCODER = """
/* A plane has at most 96 bytes. Return zero if literal transport is smaller. */
static unsigned pack_map512(uint8_t *dst,const uint8_t *src,unsigned span){
 unsigned out=0;
 for(unsigned lane=0;lane<2;lane++){
  for(unsigned i=lane;i<span;){
   unsigned start=i,run=1;
   while(i+2*run<span && src[i+2*run]==src[i])run++;
   if(run>=3){
    if(out+2>=span)return 0;
    dst[out++]=127+run;dst[out++]=src[i];i+=2*run;
   }else{
    i+=2;
    while(i<span && !(i+4<span && src[i]==src[i+2] && src[i]==src[i+4]))i+=2;
    unsigned n=(i-start)/2;
    if(out+1+n>=span)return 0;
    dst[out++]=n-1;
    for(unsigned j=start;j<i;j+=2)dst[out++]=src[j];
   }
  }
 }
 return out;
}
"""

MAP_HEADER = """
 c.label('map_header512');lda(0x1201);c.emit(0x29,255,0,0xc9,2,0);cond(0xd0,'bad_packet')
 lda(0x120e);cond(0xf0,'bad_packet');c.emit(0xc9,193,0);cond(0xb0,'bad_packet')
 c.emit(0x89,63,0);cond(0xd0,'bad_packet');lda(0x120c);sta(0x1260);cond(0xf0,'bad_packet')
 cmp(0x120e);cond(0xb0,'bad_packet');lda(0x120e);sta(0x120c);c.jump('data')
"""

MAP_DECODE = """
 c.label('map_decode512');c.emit(0xe2,0x20);c.store(0x7c,0x7f);c.emit(0xc2,0x20)
 c.absolute(0x9c,0x1268);c.emit(0xa2,0,0)
 c.label('map_plane512');c.absolute(0xac,0x1268)
 c.label('map_run512');c.absolute(0xec,0x1260);cond(0xb0,'bad_packet')
 c.emit(0xe2,0x20);c.long(0xbf,0x400010);c.emit(0xe8,0xc2,0x20,0x29,255,0);sta(0x1264)
 c.emit(0x29,127,0,0x1a);sta(0x1262)
 c.emit(0x0a,0x18);sta(0x1266);c.emit(0x98,0x38);c.absolute(0xed,0x1268);c.emit(0x18);c.absolute(0x6d,0x1266)
 cmp(0x120c);cond(0x90,'map_fit512');cond(0xd0,'bad_packet')
 c.label('map_fit512');lda(0x1264);c.emit(0x89,128,0);c.branch(0xf0,'map_literal512')
 c.absolute(0xec,0x1260);cond(0xb0,'bad_packet');c.emit(0xe2,0x20);c.long(0xbf,0x400010);c.emit(0xe8)
 c.label('map_repeat512');c.emit(0x97,0x7a,0xc8,0xc8);c.absolute(0xce,0x1262);c.branch(0xd0,'map_repeat512')
 c.jump('map_run_done512')
 c.label('map_literal512');c.emit(0x8a,0x18);c.absolute(0x6d,0x1262);cmp(0x1260)
 c.branch(0x90,'map_literal_fit512');cond(0xd0,'bad_packet')
 c.label('map_literal_fit512');c.emit(0xe2,0x20)
 c.label('map_copy512');c.long(0xbf,0x400010);c.emit(0xe8,0x97,0x7a,0xc8,0xc8)
 c.absolute(0xce,0x1262);c.branch(0xd0,'map_copy512')
 c.label('map_run_done512');c.emit(0xc2,0x20);call(c,'service');lda(0x1236);cond(0xd0,'stop_packet')
 c.emit(0x98,0x38);c.absolute(0xed,0x1268);cmp(0x120c);cond(0x90,'map_run512')
 lda(0x1268);cond(0xd0,'map_end512');c.absolute(0xee,0x1268);c.jump('map_plane512')
 c.label('map_end512');c.absolute(0xec,0x1260);cond(0xd0,'bad_packet');c.jump('accepted')
"""


def build_client(out):
    original = nes_output489.source

    def source(template):
        text = original(template)
        text = once(text, "checkimm(0x120e,0);c.label('packed_header181')",
                    "c.emit(0xc9,9,0);c.branch(0xf0,'packed_header181');checkimm(0x120e,0);c.label('packed_header181')")
        text = once(text, " c.label('bulk194');", MAP_HEADER + "\n c.label('bulk194');")
        text = once(text, " c.emit(0xc9,8,0);cond(0xf0,'repeat227')",
                    " c.emit(0xc9,9,0);cond(0xf0,'map_header512')\n c.emit(0xc9,8,0);cond(0xf0,'repeat227')")
        text = once(text, " lda(0x1200);c.emit(0xc9,4);c.branch(0xf0,'repeated1815')",
                    " lda(0x1200);c.emit(0xc9,9);cond(0xf0,'map_decode512');c.emit(0xc9,4);c.branch(0xf0,'repeated1815')")
        return once(text, " c.label('service');", MAP_DECODE + "\n c.label('service');")

    nes_output489.source = source
    try:
        return nes_output489.build(out)
    finally:
        nes_output489.source = original



def compact_reports(arm, out):
    """Share the bounded hex-line writer in the post-STOP SD reports."""
    import re
    name = "nes_budget210.c"
    text = (arm / name).read_text()
    marker = "int nes_budget210_format("
    helper = r"""
int nes_hexline512(char *text,unsigned size,int n,const uint8_t *p,unsigned len){
 static const char digits[]="0123456789abcdef";
 if(n<0 || (unsigned)n>=size || len>(size-(unsigned)n-1)/2 || size-(unsigned)n<2*len+2)return -1;
 for(unsigned i=0;i<len;i++){text[n++]=digits[p[i]>>4];text[n++]=digits[p[i]&15];}
 text[n++]='\n';text[n]=0;return n;
}
"""
    text = once(text, marker, helper + marker)
    pattern = r' for\(unsigned i=0;i<20;i\+\+\)\{\n  int hex=snprintf\(text\+n,size-\(unsigned\)n,"%02x",\(unsigned\)([\w.]+)\[i\]\);.*?text\[n\+\+\]=\'\\n\';text\[n\]=0;'
    text, count = re.subn(pattern, lambda m: " n=nes_hexline512(text,size,n,"+m[1]+",20);if(n<0)return -1;", text, flags=re.S)
    assert count == 3
    (out / name).write_text(text)
    name = "nes_menu_diagnostic.c"
    text = (arm / name).read_text()
    text = once(text, "static int history165_format(", "extern int nes_hexline512(char *,unsigned,int,const uint8_t *,unsigned);\nstatic int history165_format(")
    a = text.index('  used=snprintf(text+n,size-(size_t)n,"ppu_history_%02u=')
    b = text.index("\n }", a)
    text = text[:a] + '''  used=snprintf(text+n,size-(size_t)n,"ppu_history_%02u=",i);
  if(used<0||(size_t)used>=size-(size_t)n)return -1;
  n=nes_hexline512(text,size,n+used,h,12);if(n<0)return -1;''' + text[b:]
    (out / name).write_text(text)



def arm_patches(arm, out, map_change, input_change):
    out.mkdir(parents=True, exist_ok=False)
    if map_change:
        compact_reports(arm, out)
        name = "nes_native_sink165.c"
        text = (arm / name).read_text()
        text = once(text, "static bool packet_wire", MAP_ENCODER + "\nstatic bool packet_wire")
        text = once(text, " put16(b+12,n);if(n)memcpy(b+16,data,n);", """
 unsigned packed=0;
 if(b[0]==2 && section==2 && n && n<=192 && !(n&63))packed=pack_map512(b+16,data,n);
 if(packed){b[0]=9;put16(b+14,n);n=packed;}
 else if(n)memcpy(b+16,data,n);
 put16(b+12,n);""")
        (out / name).write_text(once(text, "b[0]==8||bulk_submit", "b[0]==8||b[0]==9||bulk_submit"))
        name = "nes_sink_window184.c"
        text = (arm / name).read_text()
        (out / name).write_text(once(text, "p[0]!=8&&p[0]!=7", "p[0]!=8&&p[0]!=9&&p[0]!=7"))
    if input_change:
        name = "nes_native165.c"
        text = (arm / name).read_text()
        a = text.index(" for(unsigned pos=0;pos<n;)")
        b = text.index("  unsigned width=", a)
        text = text[:a] + """ if(n<6||p[0]!=0x51)return fail(s,19);
 unsigned gen=((unsigned)p[1]<<8)|p[2];
 for(unsigned pos=3;pos<n;){
  if(n-pos<2)return fail(s,19);
  unsigned tag=((unsigned)p[pos]<<8)|p[pos+1],kind=tag>>13,index=tag&8191;pos+=2;
  if(kind==7&&(index==1||index==2||index==3)&&(pos!=5||n!=13))return fail(s,19);
""" + text[b:]
        (out / name).write_text(text)



def share_crc(arm, out):
    """Use the receiver's same-polynomial routines on actual E1/E8/E9 packets."""
    import re
    def get(name):
        patch = out / name
        return (patch if patch.exists() else arm / name).read_text()
    name = "nes_native165.c"
    s = get(name)
    s = s.replace("static uint16_t crc16(", "uint16_t nes_crc16_512(").replace("static uint8_t crc8(", "uint8_t nes_crc8_512(")
    s = s.replace("crc16(", "nes_crc16_512(").replace("crc8(", "nes_crc8_512(")
    (out / name).write_text(s)
    for name in ("nes_plan_service200.c", "nes_sink_window184.c"):
        s = get(name)
        for bits in (8,16):
            s, n = re.subn(r"static uint"+str(bits)+r"_t crc"+str(bits)+r"\([^\n]+\n",
                          f"extern uint{bits}_t nes_crc{bits}_512(const uint8_t *,unsigned);\n", s)
            assert n == 1
        if name == "nes_sink_window184.c":
            s = once(s, "uint8_t c=0;for(unsigned i=1;i<19;i++)c=crc8(c,rx[i]);", "uint8_t c=nes_crc8_512(rx+1,18);")
            s = once(s, "uint16_t c=0xffff;\n for(unsigned i=0;i<=n;i++)c=crc16(c,tx[i]);", "uint16_t c=nes_crc16_512(tx,n+1);")
        else:
            s = s.replace("crc8(", "nes_crc8_512(").replace("crc16(", "nes_crc16_512(")
        (out / name).write_text(s)



def input_packets(geometry, raw, generation):
    blocks, counts, arrays = encode(geometry, raw, generation)
    header = b"\x51" + generation.to_bytes(2, "big")
    output = []
    buf = bytearray(header)
    for block in blocks:
        at = 0
        while at < len(block):
            tag = int.from_bytes(block[at:at + 2], "big")
            kind, index = tag >> 13, tag & 8191
            width = 8 if kind == 0 and index & 4096 else (2, 1, 7, 4, 7, 1, 2, 8)[kind]
            assert block[at + 2:at + 4] == header[1:]
            record = block[at:at + width + 4]
            assert len(record) == width + 4
            at += len(record)
            terminal = kind == 7 and index in (1, 2)
            if terminal and len(buf) > 3:
                output.append(bytes(buf))
                buf = bytearray(header)
            buf += record[:2] + record[4:]
            if len(buf) > 246 or (kind == 7 and 0 < index < 0x800):
                assert len(buf) <= 256
                output.append(bytes(buf))
                buf = bytearray(header)
    assert buf == header
    return output, counts, arrays


def legacy_packets(geometry, raw, generation):
    """Original FPGA seals after a completed record at >244 bytes or any control marker."""
    template, counts, arrays = encode(geometry, raw, generation)
    output = []
    current = bytearray()
    for block in template:
        pos = 0
        while pos < len(block):
            tag = int.from_bytes(block[pos:pos+2], "big")
            kind, index = tag >> 13, tag & 8191
            width = 8 if kind == 0 and index & 4096 else (2,1,7,4,7,1,2,8)[kind]
            current += block[pos:pos+4+width]
            pos += 4+width
            if len(current) > 244 or (kind == 7 and 0 < index < 0x800):
                assert len(current) <= 256
                output.append(bytes(current))
                current.clear()
    assert not current
    return output, counts, arrays


def input_rtl(board, out):
    name = "nes_native_spi165.sv"
    text = (board / name).read_text()
    text = once(text, "0:pack_byte=tag[15:8];1:pack_byte=tag[7:0];2:pack_byte=held[92:85];3:pack_byte=held[84:77];",
                "0:pack_byte=8'h51;1:pack_byte=held[92:85];2:pack_byte=held[84:77];3:pack_byte=tag[15:8];4:pack_byte=tag[7:0];")
    text = once(text, "assign record_ready=!reset&&!sealed&&!encoding&&used<=244;", """
 wire terminal=record_data[95:93]==7 && (record_data[76:64]==1 || record_data[76:64]==2);
 wire separate_terminal=record_valid && terminal && used!=0;
 assign record_ready=!reset&&!fault&&!sealed&&!encoding&&used<=246&&!separate_terminal;""")
    text = once(text, "if(record_valid&&record_ready)begin held<=record_data;position<=0;total<=4+", """if(!encoding && separate_terminal)sealed<=1;
   if(record_valid&&record_ready && used!=0 && record_data[92:77]!=held[92:77])fault<=1;
   else if(record_valid&&record_ready)begin held<=record_data;position<=used==0?0:3;total<=5+""")
    text = once(text, "if(used+1>244", "if(used+1>246")
    (out / name).write_text(text)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("arm", "board", "out"):
        p.add_argument("--" + n, type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    build_client(a.out / "client")
    input_rtl(a.board, a.out)
    for label in ("map", "input", "both"):
        arm_patches(a.arm, a.out / label, label != "input", label != "map")
        if label != "input":
            share_crc(a.arm, a.out / label)
