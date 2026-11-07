"""Bounded map run encoding; each accepted legacy block keeps its original token."""
import argparse
import binascii
import shutil
import struct
from pathlib import Path
from nes_raw506 import once,sha
from nes_transfer512 import legacy_packets as legacy
from check_nes_fault641 import evidence

# Each lookup has a fixed interpretation in SNES map-cell order. References
# cannot reach a prior packet, frame, bank, or unvalidated part of the map.
DISTANCES=(1,2,4,33)
MARK=0xffff


def pack(cells,start,gen):
    raw=struct.pack("<"+"H"*len(cells),*cells)
    output=bytearray(struct.pack(">HHHHH",MARK,gen,start,len(cells),binascii.crc_hqx(raw,65535)))
    literals=[]
    def flush():
        if literals:
            output.append(len(literals)-1)
            output.extend(struct.pack("<"+"H"*len(literals),*literals))
            literals.clear()
    pos=0
    while pos<len(cells):
        best=0
        for lane,dist in enumerate(DISTANCES):
            if dist>pos:continue
            count=0
            while count<32 and pos+count<len(cells) and cells[pos+count]==cells[pos+count-dist]:
                count+=1
            if count>best:best,selector=count,lane
        if best>=2:
            flush()
            output.append(128+32*selector+best-1)
            pos+=best
        else:
            literals.append(cells[pos]);pos+=1
            if len(literals)==128:flush()
    flush()
    return bytes(output)


def encode(geometry,raw,generation):
    original,counts,arrays=legacy(geometry,raw,generation)
    packets=original.copy()
    cursor=0
    for i,block in enumerate(original[:7]):
        head=12 if i==0 else 0
        if head:assert block[:2]==bytes.fromhex("e000")
        p=head;cells=[]
        while p<len(block):
            key,g=struct.unpack_from(">HH",block,p)
            assert g==generation
            if key>>12==1:
                v=int.from_bytes(block[p+4:p+12],"big");n=v>>60
                assert (key&4095)==cursor+len(cells) and 1<=n<=4
                cells.extend((v>>(15*j))&32767 for j in reversed(range(n)));p+=12
            elif key>>8==0xd0:
                v=int.from_bytes(block[p+4:p+6],"big");cells.extend([v]*((key&255)+1));p+=6
            else:break
        if p!=len(block):break
        assert cells==arrays[0][cursor:cursor+len(cells)]
        new=block[:head]+pack(cells,cursor,generation)
        if len(new)<len(block):packets[i]=new
        cursor+=len(cells)
    return packets,counts,arrays


DECODER="""
/* Per-block map extent; previous block history is never referenced. */
static bool restore650(struct nes_native165 *s,unsigned gen,const uint8_t *b,unsigned n){
 static const uint8_t distance[4]={1,2,4,33};
 if(n<6 || s->state!=NES_NATIVE165_RECEIVING || s->next_kind!=0 ||
    s->generation!=gen)return fail(s,36);
 unsigned start=(b[0]<<8)|b[1],count=(b[2]<<8)|b[3],expected=(b[4]<<8)|b[5];
 if(start!=s->at[0] || start>=s->counts[0] || !count || count>s->counts[0]-start)
  return fail(s,36);
 uint16_t *dst=s->maps+start;
 unsigned at=0,i=6;
 while(i<n){
  unsigned cmd=b[i++],copy=cmd&128,len=(copy?(cmd&31):cmd)+1;
  if(len>count-at)return fail(s,36);
  if(copy){
   unsigned back=distance[(cmd>>5)&3];
   if(back>at)return fail(s,36);
   while(len--){dst[at]=dst[at-back];at++;}
  }else{
   if(2*len>n-i)return fail(s,36);
   while(len--){
    unsigned v=b[i]|(b[i+1]<<8);i+=2;
    if(v>>15)return fail(s,36);
    dst[at++]=(uint16_t)v;require_tile(s,v&8191u,1);
   }
  }
 }
 if(at!=count || crc_xmodem_block(0xffff,(const uint8_t *)dst,2*at)!=expected)
  return fail(s,36);
 s->at[0]+=count;s->records+=count;return true;
}
"""


def prepare(base,out,mode):
    j=evidence("receive649-verification.json")
    pinned=j["guards"]["sealed"]["firmware"] if mode=="sealed" else j["phases"]["1"]["648"]["schedule"]["firmware_SHA256"]
    assert sha(base/"src/obj-nes-100/firmware.stm")==pinned
    shutil.copytree(base,out,ignore=shutil.ignore_patterns("obj-*",".dep-*","*.log","base-*"))
    f=out/"src/nes_native165.c";s=f.read_text()
    s=once(s,"bool nes_native165_packet(",DECODER+"\nbool nes_native165_packet(")
    s=once(s,"  unsigned width=(kind==0&&", """  if(tag==65535){
   if(!restore650(s,gen,p+pos,n-pos))return false;
   pos=n;break;
  }
  unsigned width=(kind==0&&""")
    f.write_text(s,newline="\n")
    if mode=="once":
        # At most one pre-SEAL offer from the sealed-END path. A receiver
        # that has consumed the old COMMIT cannot restart the budget.
        plan=out/"src/nes_plan_service200.c"
        plan.write_text(once(plan.read_text(),"p->bulk_until=p->window->sent;","""p->bulk_until=p->window->sent;
   if(phase==NES_PLAN215_FINISH && rx[3]==2 && p->window->wait &&
      !p->window->wait(p->ctx,p->guard,4,false))return fail(p,2);"""),newline="\n")
        runtime=out/"src/nes_native_runtime165.c"
        code=once(runtime.read_text()," if(reason==3){",""" if(reason==4){
  if(s->receiver->state!=NES_NATIVE165_COMMITTED)return check(ctx);
  reason=3;
 }
 if(reason==3){""")
        code=once(code,"   --s->prefetch_left;","   uint16_t before=r->next_token;--s->prefetch_left;")
        code=once(code,"if(!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);\n  }",
                       "if(!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);\n   progress=r->next_token!=before;\n  }")
        runtime.write_text(code,newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("base",type=Path);p.add_argument("out",type=Path);p.add_argument("mode",choices=("packed","sealed","once"))
    a=p.parse_args();prepare(a.base,a.out,a.mode)
