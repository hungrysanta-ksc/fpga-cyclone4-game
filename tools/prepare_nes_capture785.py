# SPDX-License-Identifier: MIT
"""Timed changes to the 783G receive/retire path, with COMMIT fenced by final ACK and EA."""
import argparse
import re
from pathlib import Path
from nes_raw506 import once, sha

BASE_ELF = "e39c66995900e635da42b87567e84d51f73ba00cd0f1203b79447e72c315093f"


def fold_crc(source):
    return once(source,"for(unsigned i=0;i<8;i++)c=(uint8_t)((c<<1)^((c&128)?7:0));",
                "unsigned folded=c^(c>>6)^(c>>7);c=(uint8_t)(folded^(folded<<1)^(folded<<2));")


def shrink_report(base, out):
    # The same checked formatter already returns the accumulated offset or -1.
    # Reuse it for post-session diagnostics; preserve all truncation outcomes.
    name="nes_menu_diagnostic.c"
    source=(base/name).read_text()
    pattern=r"int used=nes_report594\(text\+n,4096-\(size_t\)n,\(const unsigned char \*\)([^;]+);\n  n=used<0\|\|\(size_t\)used>=4096-\(size_t\)n\?-1:n\+used;"
    source,count=re.subn(pattern,lambda m:"n=nes_report_packed782(text,4096,n,"+m[1]+";",source)
    assert count==2
    pattern=r"extra=nes_report594\(text\+n,4096-\(unsigned\)n,\(const unsigned char \*\)([^;]+);\n if\(extra<0\|\|\(unsigned\)extra>=4096-\(unsigned\)n\)return;\n n\+=extra;"
    source,count=re.subn(pattern,lambda m:"n=nes_report_packed782(text,4096,n,"+m[1]+";\n if(n<0)return;",source)
    assert count==2
    (out/name).write_text(source,newline="\n")
    name="nes_budget210.c"
    source=(base/name).read_text()
    source=once(source,"len>(size-(unsigned)n-1)/2 || size-(unsigned)n<2*len+2","size-(unsigned)n<2 || len>(size-(unsigned)n-2)/2")
    (out/name).write_text(source,newline="\n")


def shrink_headers(out):
    # Use the same checked append for both bounded controller/history headers.
    name="nes_menu_diagnostic.c"
    source=(out/name).read_text()
    pattern=r"(?:int )?used=nes_report594\(text\+n,size-\(size_t\)n,\(const unsigned char \*\)([^;]+);\n( +)if\(used<0\|\|\(size_t\)used>=size-\(size_t\)n\)return -1;\n +n\+=used;"
    source,count=re.subn(pattern,lambda m:"n=nes_report_packed782(text,size,n,"+m[1]+";\n"+m[2]+"if(n<0)return -1;",source)
    assert count==3
    source=once(source,"  used=snprintf(text+n","  int used=snprintf(text+n")
    (out/name).write_text(source,newline="\n")


def prepare(base, out, mode):
    assert sha(base/"obj-nes-100/sd2snes.elf")==BASE_ELF
    out.mkdir(parents=True,exist_ok=False)
    if mode in ("sealed","sealed_poll","sealed_fit","sealed_compact","sealed_history"):
        packed=mode in ("sealed_fit","sealed_compact","sealed_history")
        # Limit the fast handoff to an output wait that actually receives
        # the END packet. Cold and foreground input use the original ordering.
        shrink_report(base,out)
        name="nes_native165.c"
        source=(base/name).read_text()
        source=once(source,"if(s->state==NES_NATIVE165_RECEIVING && (rx[2]&1)){",
            "if((s->state==NES_NATIVE165_RECEIVING && (rx[2]&1)) || (s->state==NES_NATIVE165_COMPLETE && (rx[2]&2))){")
        source=once(source,"s->ready183=false;\n uint8_t tx[8],rx[8];frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8)||!status(rx)||!(rx[2]&2))return fail(s,25);","""bool sealed=s->ready183;s->ready183=false;
 uint8_t tx[8],rx[8];
 if(sealed){memcpy(rx,s->status183,8);}
 else{frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8))return fail(s,25);}
 if(!status(rx)||!(rx[2]&2)||(uint16_t)(rx[3]*256u+rx[4])!=s->next_token)return fail(s,25);""")
        source=once(source," s->state=accept?NES_NATIVE165_PREPARED", """ if(sealed && accept && (rx[2]&1)){memcpy(s->status183,rx,8);s->ready183=true;}
 s->state=accept?NES_NATIVE165_PREPARED""")
        (out/name).write_text(source,newline="\n")
        name="nes_native_runtime165.c"
        runtime=once((base/name).read_text(),"if(!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);\n }\n nes_trace166.receive_ticks",
            "if(!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);\n  if(r->state==NES_NATIVE165_COMPLETE)r->ready183=false;\n }\n nes_trace166.receive_ticks")
        if mode=="sealed_poll":
            runtime=once(runtime," return nes_cost474_pause(ctx,check,reason,progress);",
                " if(reason==2 && r->state==NES_NATIVE165_COMPLETE && r->ready183)return check(ctx);\n return nes_cost474_pause(ctx,check,reason,progress);")
        (out/name).write_text(runtime,newline="\n")
        if packed:
            # The shift/XOR CRC implementation frees space and uses the same polynomial.
            source=(out/"nes_native165.c").read_text()
            source=fold_crc(source)
            (out/"nes_native165.c").write_text(source,newline="\n")
            shrink_headers(out)
            if mode in ("sealed_compact","sealed_history"):
                # Both append helpers accept -1 as a sticky truncation. The
                # externally visible format function keeps its final error test.
                name="nes_budget210.c"
                text=(out/name).read_text()
                lo=text.index("int nes_budget210_format")
                hi=text.index(" for(unsigned i=0;i<12;i++)",lo)
                prefix=text[lo:hi].replace("if(n<0)return -1;", "")
                text=text[:lo]+prefix+text[hi:]
                (out/name).write_text(text,newline="\n")
                if mode=="sealed_history":
                    name="nes_menu_diagnostic.c"
                    text=(out/name).read_text()
                    text=once(text,'int used=snprintf(text+n,size-(size_t)n,"ppu_history_%02u=",i);\n  if(used<0||(size_t)used>=size-(size_t)n)return -1;\n  n=nes_hexline512(text,size,n+used,h,12);',
                        'n=nes_report_packed782(text,size,n,"ppu_history_%02u=",i);\n  n=nes_hexline512(text,size,n,h,12);')
                    (out/name).write_text(text,newline="\n")
        return
    scoped=mode=="owned"
    if scoped:mode="retire_cache"
    direct_retire=mode in ("retire","retire_cache","retire_full")
    if direct_retire:
        mode={"retire":"retire","retire_cache":"cache_fit","retire_full":"fused"}[mode]
    if mode in ("fused","compact"):
        shrink_report(base,out)
        shrink_headers(out)
    if mode.endswith("_fit"):
        shrink_report(base,out)
        mode=mode[:-4]
    if mode in ("crc","handoff","cache_crc","fused"):
        name="nes_native165.c"
        source=(base/name).read_text()
        # Reducing x*256 modulo 0x107 leaves x*(1+X+X^2).
        # The two overflow bits must themselves be reduced by the same polynomial.
        source=fold_crc(source)
        (out/name).write_text(source,newline="\n")
    if mode in ("handoff","poll","cache_poll","fused","compact"):
        name="nes_native_runtime165.c"
        source=(base/name).read_text()
        # Input COMPLETE cannot borrow SPI. Poll for the SEAL receipt again
        # after servicing STOP. through() still validates the full ACK identity.
        source=once(source," return nes_cost474_pause(ctx,check,reason,progress);",
            """ if(reason==2 && r->state==NES_NATIVE165_COMPLETE)return check(ctx);
 return nes_cost474_pause(ctx,check,reason,progress);""")
        (out/name).write_text(source,newline="\n")

    if mode in ("cache","cache_poll","cache_crc","fused","compact"):
        name="nes_native165.c"
        source=((out/name) if (out/name).exists() else (base/name)).read_text()
        # A D0 snapshot is reusable only while the source owns that head.
        # Every READ still authenticates data, token, and the retirement.
        source=once(source,"bool nes_native165_poll(", """static bool query785(struct nes_native165 *s,nes_native165_transfer_fn fn,void *ctx,uint8_t *rx){
 static const uint8_t tx[8]={0xd0,0,0,0,0,0xff,CRC_D0,0xa5};
 return fn(ctx,tx,rx,8)&&status(rx);
}
static void cache785(struct nes_native165 *s,const uint8_t *rx){
 memcpy(s->status183,rx,8);s->ready183=true;
}
bool nes_native165_poll(""".replace("CRC_D0",str(crc8(bytes([0xd0,0,0,0,0,255])))))
        source=once(source,"else {frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8))return fail(s,21);}", "else if(!query785(s,fn,ctx,rx))return fail(s,21);")
        source=once(source,"frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8)||!status(rx)||\n","if(!query785(s,fn,ctx,rx)||\n")
        source=once(source,"if(s->state==NES_NATIVE165_RECEIVING && (rx[2]&1)){\n  memcpy(s->status183,rx,8);s->ready183=true;", """if((s->state==NES_NATIVE165_RECEIVING && (rx[2]&1)) ||
    (s->state==NES_NATIVE165_COMPLETE && (rx[2]&2))){
  cache785(s,rx);""")
        source=once(source,"s->ready183=false;\n uint8_t tx[8],rx[8];frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8)||!status(rx)||!(rx[2]&2))return fail(s,25);","""uint8_t tx[8],rx[8];
 if(s->ready183){
  memcpy(rx,s->status183,8);s->ready183=false;
  if(!status(rx))return fail(s,25);
 }else if(!query785(s,fn,ctx,rx))return fail(s,25);
 if(!(rx[2]&2)||(uint16_t)(rx[3]*256u+rx[4])!=s->next_token)return fail(s,25);""")
        source=once(source,"frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8)||!status(rx))return fail(s,28);","""if(!query785(s,fn,ctx,rx))return fail(s,28);
 if(accept && (rx[2]&1))cache785(s,rx);""")
        (out/name).write_text(source,newline="\n")

    if direct_retire:
        # FINISH proves END + empty descriptor. Only EA can retire this plan.
        # The existing FPGA EA controller checks generation/count/idle again
        # at chip-select release. Verify E8 rearm before permitting COMMIT.
        name="nes_plan_service200.c"
        source=(base/name).read_text()
        source=once(source,"if(flags&2){p->finished=true;return true;}",
            "if(flags&2){if(flags!=2)return fail(p,4);p->finished=true;return true;}")
        begin=source.index(" uint8_t rx[20];bool sent=false;")
        end=source.index("   p->sent=0;",begin)
        emit=source[source.index("   uint8_t cmd[7]",begin):source.index("   sent=true;",begin)]
        source=source[:begin]+emit+""" uint8_t rx[20];
 for(unsigned i=0;i<p->poll_limit;i++){
  if(!p->guard(p->ctx))return fail(p,2);
  const uint8_t phase=NES_PLAN215_REARM;
  if(!read509(p,rx,phase))return false;
  if(rx[3]&0xf8)return status215(p,phase,NES_PLAN215_FLAGS,rx);
  for(unsigned k=6;k<19;k++)if(rx[k])return status215(p,phase,NES_PLAN215_EMPTY,rx);
  unsigned accepted=(unsigned)rx[4]*256+rx[5];
  if(rx[3]==1&&accepted==0){
"""+source[end:]
        if scoped:
            # Retain the original live E8 when the next frame still needs data.
            # This decision uses actual checked input completion, never a frame ID.
            source=once(source,"bool nes_plan200_retire(struct nes_plan200 *p){",
                "bool nes_plan200_retire_owned(struct nes_plan200 *p,bool complete){")
            anchor="   uint8_t cmd[7]"
            source=once(source,anchor,""" if(!complete){
  uint8_t status[20];const unsigned phase=NES_PLAN215_RETIRE;
  if(!p->guard(p->ctx))return fail(p,2);
  if(!read509(p,status,phase))return false;
  if(status[3]!=2 || (unsigned)status[4]*256+status[5]!=p->sent)return status215(p,phase,NES_PLAN215_RETIRE_STATE,status);
  for(unsigned k=6;k<19;k++)if(status[k])return status215(p,phase,NES_PLAN215_EMPTY,status);
 }
"""+anchor)
            source+="\nbool nes_plan200_retire(struct nes_plan200 *p){return nes_plan200_retire_owned(p,false); }\n"
            header="nes_plan_service200.h"
            decl="bool nes_plan200_retire("
            (out/header).write_text(once((base/header).read_text(),decl,"bool nes_plan200_retire_owned(struct nes_plan200 *,bool);\n"+decl),newline="\n")
            runtime="nes_native_runtime165.c"
            code=once((base/runtime).read_text(),"nes_plan200_retire(&s->plan)","nes_plan200_retire_owned(&s->plan,r->state==NES_NATIVE165_COMPLETE)")
            (out/runtime).write_text(code,newline="\n")
        (out/name).write_text(source,newline="\n")


def crc8(data):
    c=0
    for b in data:
        c^=b
        for i in range(8):
            c=((c<<1)^(7 if c&128 else 0))&255
    return c


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("base",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("mode",choices=("crc","poll","handoff","cache","cache_poll","cache_crc","cache_fit","cache_poll_fit","cache_crc_fit","handoff_fit","poll_fit","fused","compact","retire","retire_cache","retire_full","owned","sealed","sealed_poll","sealed_fit","sealed_compact","sealed_history"))
    a=p.parse_args()
    prepare(a.base,a.out,a.mode)
