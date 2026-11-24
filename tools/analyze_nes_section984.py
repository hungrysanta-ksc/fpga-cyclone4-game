"""Account for wire, target CPU time, and frame deadlines separately."""
import argparse
import json
import os
import subprocess
from pathlib import Path

from check_nes_bg976 import map_payloads
from check_nes_blank959 import rows
from check_nes_menu533 import check as menu
from check_nes_output970 import packet_path
from check_nes_plan975 import directory, milliseconds, read, sha
from check_nes_tail979 import display
from nes_section984 import WORK, baseline
from test_nes_raw506_joint import PERIOD


def fallback():
    # Exercise every byte whose omission depends on the ARM eligibility check.
    # Build the very same C helper on the host, with no ROM/scene identifiers.
    cc=Path("C:/altera_lite/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe")
    src=(WORK/"link/src/nes_native_sink165.c").read_text()
    helper=src[src.index("static bool compact_tail984("):src.index("bool nes_sink212_seal(")]
    test=WORK/"fallback984.c"
    test.write_text("""#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <assert.h>
static void put16(uint8_t *p,unsigned v){ p[0]=v; p[1]=v>>8; }
"""+helper+"""
int main(void){
 uint8_t raw[192],t[243]={0},out[75];
 uint16_t n[]={21,21,21};
 for(unsigned i=0;i<192;i++)raw[i]=(uint8_t)(i/64+31*(i%2));
 for(unsigned i=0;i<3;i++)
  for(unsigned k=0;k<21;k++)t[i*81+k]=(uint8_t)(19*i+k);
 assert(compact_tail984(out,raw,t,n));
 for(unsigned i=0;i<3;i++){
  assert(out[2*i]==21 && !out[2*i+1]);
  assert(!memcmp(out+6+2*i,raw+i*64,2));
  assert(!memcmp(out+12+21*i,t+i*81,21));
 }
 for(unsigned i=0;i<192;i++){
  raw[i]^=1;assert(!compact_tail984(out,raw,t,n));raw[i]^=1;
 }
 for(unsigned i=0;i<3;i++){
  for(unsigned k=21;k<81;k++){
   t[i*81+k]=1;assert(!compact_tail984(out,raw,t,n));t[i*81+k]=0;
  }
  n[i]=20;assert(!compact_tail984(out,raw,t,n));n[i]=21;
 }
 assert(compact_tail984(out,raw,t,n));
 return 0;
}
""")
    exe=WORK/"fallback984.exe"
    env=dict(os.environ,PATH=str(cc.parent)+os.pathsep+os.environ["PATH"])
    subprocess.run([cc,"-std=c11","-O2",test,"-o",exe],env=env,check=True)
    subprocess.run([exe],env=env,check=True)
    return dict(repeated_raw_bytes=192,padding_bytes=180,table_lengths=3)


def measure(temp,phase,tag):
    d=directory(temp,phase,tag,"cold")
    ref=directory(temp,phase,"978returned","cold")
    compact=tag=="984compact"
    for g in range(905,913):
        assert sha(d/f"frame-{g}.rgb")==sha(ref/f"frame-{g}.rgb")
    assert map_payloads(d)==map_payloads(ref)
    records=lambda folder:[(x["g"],x["records"]) for x in read(folder/"e9931.json")]
    assert records(d)==records(ref)
    cs,ledger=packet_path(d,911,expected_shape=(15,3) if compact else (16,3))
    tail=[]
    for c,r in zip(cs[-len(ledger):],ledger,strict=True):
        b=bytes.fromhex(c[3])
        if b[1]==5 and int.from_bytes(b[10:12],"little")>=1121:
            tail.append(dict(**r,payload=len(b)-16))
    assert [r["payload"] for r in tail]==([75] if compact else [201,240])
    events=read(d/"events.json")
    ready,=(e["capture_ready"] for e in events if e["event"]=="source_begin" and e["generation"]==911)
    j=read(d/"joint.json")
    ack909,=(f["ACK_masterclock"] for f in j["frames"] if f["generation"]==909)
    origin=ready-240*341*4
    target=origin+round((ack909-origin)/PERIOD)*PERIOD
    last_d2=max(e["clock"] for e in events if e.get("input_generation")==910 and e.get("opcode")=="0xd2")
    v=[int(x["frame"]) for x in rows(d/"window.csv") if x["event"]=="reveal"]
    m=display(d)
    return dict(tail=tail,wire_B=sum(r["payload"]+19 for r in tail),
                spi_ms=milliseconds(sum(r["arrive"]-r["issue"] for r in tail)),
                service_ms=milliseconds(sum(r["ack"]-r["load"] for r in tail)),
                reveal_VB=v,interval911=v[-2]-v[-3],six=v[-1]-v[1],
                reveal908=m["reveal908"],seal911=m["seal"],early909_B=m["early909_B"],
                capture910_margin_ms=milliseconds(target-last_d2),ACK912=j["frames"][-1]["ACK_masterclock"],
                firmware=j["firmware_SHA256"],client=sha(d/"client.sfc"),matched_rgb=8)


def analyze(temp):
    result=dict(phases={},fallback_host_C=fallback(),guards={})
    for phase in (1,2):
        cases={tag:measure(temp,phase,tag) for tag in ("978returned","984literal","984compact")}
        result["phases"][phase]=cases
        assert cases["984literal"]["client"]==cases["984compact"]["client"]
        assert cases["984literal"]["firmware"]==cases["978returned"]["firmware"]
        for v in cases.values():
            v["final_delta_ms"]=milliseconds(v["ACK912"]-cases["978returned"]["ACK912"])
    for fault in ("normal","partial","damage","seal"):
        d=temp/f"nes-984check2-1-{fault}"
        r=read(d/"result.json")
        assert r["passed"] and r["commits"]==(7 if fault=="normal" else 6)
        if fault!="normal":
            assert r["last_status"]==(228 if fault=="partial" else 224)
            assert sha(d/"retained.rgb")==sha(directory(temp,1,"978returned","cold")/"frame-910.rgb")
            ack=[x for x in rows(d/"window.csv") if x["event"]=="ack"][-1]
            if fault in ("partial","damage"):
                assert (ack["g"],ack["op"],ack["section"])==("911","9","5")
                assert int(ack["value"])==r["last_status"]
        result["guards"][fault]=[r["commits"],r["last_status"]]
    m=menu(WORK/"link/src","966")
    assert m["firmware"]==result["phases"][1]["984compact"]["firmware"]
    result["menu"]={k:v["released"] for k,v in m["rows"].items()}
    rom=read(WORK/"client/build.json")
    result["sizes"]=dict(arm_B=next((WORK/"link").rglob("firmware.stm")).stat().st_size,
                         baseline_arm_B=next((baseline("returned")/"link").rglob("firmware.stm")).stat().st_size,
                         arm_limit_B=212992,rom_B=rom["loader_B"]+rom["encoded_B"],rom_limit_B=5056)
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp),indent=2)+"\n",encoding="utf-8")
