# SPDX-License-Identifier: MIT
"""Build the MMC509 bank-aware literal edge trim. No source SPI format change."""
import argparse
import inspect
import json
from pathlib import Path
import nes_dirty212
import nes_output489
from nes_raw506 import once, sha
from nes_transfer512 import compact_reports, share_crc

# Metadata 1260..1261: independently published bank-valid flags.
# 1262: edge CRC; 1264: rounded start; 1266: rounded length.
CHECK = """
 c.label('edge514');c.absolute(0xae,0x1034);c.emit(0xe2,0x20)
 c.absolute(0xbd,0x1260);c.emit(0xc2,0x20,0x29,255,0);cond(0xf0,'bad_packet')
 lda(0x62);c.absolute(0x0d,0x64);c.emit(0x89,7,0);cond(0xd0,'bad_packet')
 lda(0x62);c.emit(0x29,0xc0,0xff);sta(0x1264)
 lda(0x1234);c.emit(0x18,0x69,63,0,0x29,0xc0,0xff,0x38);c.absolute(0xed,0x1264);sta(0x1266)
 c.emit(0xc9,193,0);cond(0xb0,'bad_packet');cmp(0x64);cond(0xf0,'bad_packet')
 imm(65535);sta(0x1262)
 lda(0x62);c.emit(0x38);c.absolute(0xed,0x1264);c.emit(0xa8)
 lda(0x1264);call(c,'edge_span514')
 lda(0x1264);c.emit(0x18);c.absolute(0x6d,0x1266);c.emit(0x38);c.absolute(0xed,0x1234);c.emit(0xa8)
 lda(0x1234);call(c,'edge_span514')
 lda(0x1262);cmp(0x120e);cond(0xd0,'bad_packet')
 call(c,'service');lda(0x1236);cond(0xd0,'stop_packet')
 lda(0x1264);sta(0x62);lda(0x1266);sta(0x64);c.emit(0x60)
 c.label('edge_span514');c.emit(0xc0,0,0);c.branch(0xf0,'edge_return514')
 c.emit(0x18);c.absolute(0x6d,0x1020);c.emit(0x18,0x69,0,0x50,0xaa)
 c.label('edge_byte514');c.long(0xbf,0x7f0000);c.emit(0xeb,0x29,0,255);c.absolute(0x4d,0x1262)
 for _ in range(8):c.emit(0x0a,0x90,3,0x49,0x21,0x10)
 sta(0x1262);c.emit(0xe8,0x88);c.branch(0xd0,'edge_byte514')
 c.label('edge_return514');c.emit(0x60)
"""


def client(out, *, check=CHECK, publish="", opcode=10):
    original_source, original_emit = nes_output489.source, nes_dirty212.emit

    def source(template):
        s = original_source(template)
        s = once(s,"checkimm(0x120e,0);c.label('packed_header181')",
                 f"c.emit(0xc9,{opcode},0);c.branch(0xf0,'packed_header181');checkimm(0x120e,0);c.label('packed_header181')")
        s = once(s," c.emit(0xc9,8,0);cond(0xf0,'repeat227')",
                 f" c.emit(0xc9,{opcode},0);cond(0xd0,'ordinary514');checkimm(0x1201,2);c.jump('data');c.label('ordinary514');lda(0x1200);c.emit(0x29,255,0)\n c.emit(0xc9,8,0);cond(0xf0,'repeat227')")
        # 1201 is a single byte, followed by sequence, so compare only its low byte.
        s = once(s,"checkimm(0x1201,2)","lda(0x1201);c.emit(0x29,255,0,0xc9,2,0);cond(0xd0,'bad_packet')")
        s = once(s," c.label('fail');sta(0x122a)", " c.label('fail');c.absolute(0x9c,0x1260);sta(0x122a)")
        s = once(s,"c.label('bad_header');c.jump('quiet')","c.label('bad_header');c.absolute(0x9c,0x1260);c.jump('quiet')")
        s = once(s," c.label('quiet');call(c,'service')"," c.label('quiet');c.absolute(0x9c,0x1260);call(c,'service')")
        s = once(s," c.absolute(0xee,0x1220);lda(0x1228)",
                 """ lda(0x1228);c.branch(0xd0,'no_publish514');c.absolute(0xae,0x1034)
"""+publish+""" c.emit(0xe2,0x20,0xa9,1);c.absolute(0x9d,0x1260);c.emit(0xc2,0x20)
 c.label('no_publish514');c.absolute(0xee,0x1220);lda(0x1228)""")
        # Non-returning failures may abandon a helper call on the stack; the
        # client enters its existing terminal quiet state until reset.
        return once(s," c.label('service');",check+"\n c.label('service');")

    s=inspect.getsource(original_emit)
    s=once(s,"c.label('map_unit212');lda(0x120a);",
           f"c.label('map_unit212');lda(0x1200);c.emit(0x29,255,0,0xc9,{opcode},0);c.branch(0xd0,'full_row514');call(c,'edge514');c.jump('map_checked514')\n c.label('full_row514');lda(0x120a);")
    s=once(s,"cond(0xd0,'mark_bad212');imm(64);sta(0x66)","cond(0xd0,'mark_bad212');c.label('map_checked514');imm(64);sta(0x66)")
    s=once(s," c.absolute(0xae,0x60);pos=len(c.data);",
           f""" lda(0x1200);c.emit(0x29,255,0,0xc9,{opcode},0);c.branch(0xd0,'descriptor514')
 lda(0x120a);sta(0x62);lda(0x120c);sta(0x64)
 c.label('descriptor514');c.absolute(0xae,0x60);pos=len(c.data);""")
    s=once(s," c.label('coverage212');c.emit", """ c.label('coverage212');c.absolute(0xae,0x1034)
 c.emit(0xe2,0x20);c.absolute(0xbd,0x1260);c.emit(0xc2,0x20,0x29,255,0);c.branch(0xd0,'bank_known514')
 for at in range(0x1310,0x1318,2):
  lda(at);c.emit(0xc9,255,255);cond(0xd0,'mark_bad212')
 c.label('bank_known514');c.emit""")
    ns=dict(nes_dirty212.__dict__)
    exec(compile(s,"mark514","exec"),ns)
    nes_output489.source,nes_dirty212.emit=source,ns["emit"]
    try:
        return nes_output489.build(out)
    finally:
        nes_output489.source,nes_dirty212.emit=original_source,original_emit


SEND = """
 const uint8_t *mask=r->map_groups[r->target];
 for(unsigned g=0;g<64;){
  if(!mask[g]){g++;continue;}
  unsigned first=g++,count=1;
  while(g<64 && count<3 && mask[g]){g++;count++;}
  unsigned at=first*64,n=count*64;
  unsigned left=__builtin_ctz((unsigned)mask[first])*8;
  unsigned right=(__builtin_clz((unsigned)mask[g-1])-24)*8;
  const uint8_t *data=p->map+at;
  if(left+right && repeat_bytes(data,n)!=n){
   uint16_t crc=nes_crcpart514(65535,data,left);
   crc=nes_crcpart514(crc,data+n-right,right);
   if(!packet_wire(s,10,2,at+left,data+left,n-left-right,crc))return false;
  }else if(!packet(s,2,2,at,data,n))return false;
 }
"""


def prepare(arm,out, *, build_client=client):
    out.mkdir(parents=True,exist_ok=False)
    patch=out/"patch"
    patch.mkdir()
    def edit(name, transform):
        target=patch/name
        s=(target if target.exists() else arm/name).read_text()
        target.write_text(transform(s),encoding="utf8",newline="\n")
    compact_reports(arm,patch)
    share_crc(arm,patch)
    edit("nes_native165.c",lambda s:once(once(s,"uint16_t nes_crc16_512(const uint8_t *p,unsigned n){\n uint16_t c=65535;",
                                               "uint16_t nes_crcpart514(uint16_t c,const uint8_t *p,unsigned n){"),
                                  "uint8_t nes_crc8_512(","uint16_t nes_crc16_512(const uint8_t *p,unsigned n){return nes_crcpart514(65535,p,n);}\nuint8_t nes_crc8_512("))
    edit("nes_native_video165.h",lambda s:once(s,"uint64_t map_dirty;","uint8_t group_dirty[64];uint64_t map_dirty;"))
    edit("nes_resident211.h",lambda s:once(once(s,"uint64_t map_stale[2],map_upload;","uint8_t map_groups[2][64];"),
                                   "nes_resident211_prepare(struct nes_resident211 *,uint64_t)","nes_resident211_prepare(struct nes_resident211 *,const uint8_t *)"))
    def resident(s):
        assert s.count("s->map_stale[0]=s->map_stale[1]=UINT64_MAX;")==2
        s=s.replace("s->map_stale[0]=s->map_stale[1]=UINT64_MAX;","memset(s->map_groups,255,sizeof s->map_groups);")
        s=once(s,"if(s->epoch!=epoch){","if(s->epoch!=epoch){\n  memset(s->map_groups,255,sizeof s->map_groups);")
        s=once(s,"uint64_t changed_from_display","const uint8_t *changed_from_display")
        left=s.index(" s->map_stale[0]|=");right=s.index("s->prepared=true;",left)
        s=s[:left]+" for(unsigned g=0;g<64;g++){s->map_groups[0][g]|=changed_from_display[g];s->map_groups[1][g]|=changed_from_display[g];}\n "+s[right:]
        return once(s,"s->map_stale[bank]=0;","memset(s->map_groups[bank],0,64);")
    edit("nes_resident211.c",resident)
    def planner(s):
        s=once(s,"p->map_dirty|=UINT64_C(1)<<(at/64)","p->group_dirty[at>>6]|=(uint8_t)(1u<<((at>>3)&7))")
        s=once(s,"p->map_dirty=inherit?0:UINT64_MAX;","if(!inherit){memset(p->group_dirty,255,sizeof p->group_dirty);}\n ")
        return once(s,"nes_resident211_prepare(resident,p->map_dirty)","nes_resident211_prepare(resident,p->group_dirty)")
    edit("nes_planner211.c",planner)
    edit("nes_budget210.c",lambda s:once(s,"uint64_t mask=v->map_dirty;while(mask){b[B210_MAP_DIRTY]++;mask&=mask-1;}",
                                          "for(unsigned row=0;row<64;row++)if(v->group_dirty[row])b[B210_MAP_DIRTY]++;"))
    def sink(s):
        s=once(s,"static bool packet_wire","extern uint16_t nes_crcpart514(uint16_t,const uint8_t *,unsigned);\nstatic bool packet_wire")
        s=once(s,"op!=8&&expanded","op!=8&&op!=10&&expanded")
        s=once(s,"b[0]==8||bulk_submit","b[0]==8||b[0]==10||bulk_submit")
        start=s.index(" for(unsigned g=0;g<64;");end=s.index(" for(unsigned k=3;",start)
        return s[:start]+SEND+s[end:]
    edit("nes_native_sink165.c",sink)
    edit("nes_sink_window184.c",lambda s:once(s,"p[0]!=8&&p[0]!=7","p[0]!=8&&p[0]!=10&&p[0]!=7"))
    build_client(out/"client")
    (out/"pins.json").write_text(json.dumps({p.name:sha(p) for p in patch.iterdir()},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("arm","out"):
        parser.add_argument("--"+key,type=Path,required=True)
    parser.add_argument("--control",action="store_true",help="Only share reporting and CRC code; leave the MMC509 packet path unchanged")
    a=parser.parse_args()
    if a.control:
        patch=a.out/"patch"
        patch.mkdir(parents=True,exist_ok=False)
        compact_reports(a.arm,patch)
        share_crc(a.arm,patch)
    else:
        prepare(a.arm,a.out)
