"""Issue the ready zero-BG/OBJ prefix through the normal checked E9 service."""
import argparse
import json
import shutil
from pathlib import Path

from check_nes_plan975 import directory, packet_path, replay
from nes_capture978 import work as baseline
from nes_cell977 import simulate
from nes_raw506 import once
from fixture_nes_port914 import fixture
from test_nes_banks557 import MASTER, host_after


def work(count):
    return baseline("returned").with_name(f"nes-head980-{count}")


def prepare(count):
    dest = work(count) / "link"
    source = baseline("returned") / "link"
    if not dest.exists():
        shutil.copytree(source, dest)
    service = dest / "src/nes_plan_service200.c"
    s = (source / "src" / service.name).read_text()
    at = " if(!append(p,q))return false;"
    contiguous = ""
    if count == 5:
        # buf[7+3] and buf[31+3] hold the first and fourth sorted slots
        # after a three-byte zero BG. Distinct resident slots cannot repeat.
        contiguous = " && p->bytes==35 && p->buffer[34]==p->buffer[10]+3 && q->mask!=255"
    if count == 9:
        # At least eight ready adjacent OBJs remain behind a newly inserted
        # lower slot. Preserve these bytes across the short E9 response.
        s = once(s, at, at + """
 if(!p->sent && p->count>=10 && p->obj_start==3 && q->kind==1 &&
    p->bytes==3+(p->count-1)*8 && p->window && p->window->last[1]==5){
  uint8_t *b=p->buffer+4;
  unsigned remaining=p->count-2;
  if(q->slot==b[6] && q->slot+1<b[14] && b[p->bytes-5]-b[14]+1==remaining){
   uint8_t saved[4];memcpy(saved,b+11,sizeof saved);
   p->bytes=11;p->count=2;
   if(!flush(p))return false;
   memcpy(b+11,saved,sizeof saved);
   memmove(b,b+11,remaining*8);
   p->count=remaining;p->bytes=remaining*8;
  }
 }""")
    else:
        s = once(s, at, at + f"""
 /* A real zero BG and a compact OBJ suffix, after the checked scroll
  * publication. No generation or token is assumed. */
 if(!p->sent && p->count=={count} && p->obj_start==3 &&
    q->kind==1 && p->window && p->window->last[1]==5{contiguous})return flush(p);""")
    # END has no variable fields other than the current generation. Use the
    # same append, framing, count, CRC and hardware validation as tile records.
    s = once(s, """static bool append(struct nes_plan200 *p,const struct nes_plan191 *q){
 uint8_t encoded[32];unsigned n=nes_plan199_encode(q,encoded);""",
             """static bool append(struct nes_plan200 *p,const uint8_t *encoded,unsigned n){""")
    s = once(s, ">q->slot){", ">encoded[3]){")
    s = once(s, at, """ uint8_t encoded[32];
 unsigned n=nes_plan199_encode(q,encoded);
 if(!append(p,encoded,n))return false;""")
    start = s.index(" struct nes_plan191 end={0};")
    end = s.index(" p->ending=true;", start)
    s = s[:start] + """ const uint8_t end[3]={0x83,p->generation,p->generation>>8};
 if(!append(p,end,sizeof end))return false;
""" + s[end:]
    service.write_text(('#pragma GCC optimize ("Oz")\n' if count == 2 else '') + s, newline="\n")
    runtime = dest / "src/nes_native_runtime165.c"
    s = (source / "src" / runtime.name).read_text()
    sent = 2 if count == 9 else count
    s = once(s, "!p->sent && p->count==14", f"((!p->sent && p->count==14) || (p->sent==1 && p->count=={14-sent}))")
    s = once(s, "return p->sent || !p->count", "return (p->sent && !s->video->prefix_due972) || !p->count")
    runtime.write_text(('#pragma GCC optimize ("Oz")\n' if count == 2 else '') + s, newline="\n")
    planner = dest / "src/nes_planner211.c"
    planner.write_text(once((source / "src" / planner.name).read_text(), " memset(p->oam,0,sizeof(p->oam));", ""), newline="\n")


def rtl_fixture(temp, phase, tag):
    root = directory(temp, phase, tag, "cold")
    events = json.loads((root/"events.json").read_bytes())
    first = next(e for e in events if e.get("opcode") == "0xe9" and e["generation"] == 911)
    accepted, packet = json.loads((root/"e9wire914-911.jsonl").read_text().splitlines()[0])
    assert first["clock"] == accepted and first["bytes"] == len(bytes.fromhex(packet))
    fixture(temp, phase, True, 911, tag, include_bg=True, earlier_origin=int(first["start"])-2048)
    d = root / "gen911"
    origin = int((d/"origin914.txt").read_text())
    bits = [7.5] + [(4+k)*8+7.5 for k in range(first["bytes"]-8)]
    ticks = [round(host_after(first["start"] + bit*MASTER/2625000, 3))-origin for bit in bits]
    (d/"admission954.txt").write_text(" ".join(map(str, [0, *ticks]))+"\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("prepare", "run", "guard", "rtl"))
    p.add_argument("count", type=int, choices=(0, 2, 5, 9))
    p.add_argument("temp", type=Path)
    p.add_argument("--phase", type=int, choices=(1, 2), default=1)
    p.add_argument("--fault", choices=("bad_seal", "stop_decode"))
    a = p.parse_args()
    tag = {0:"978returned", 2:"980checked2", 5:"980head5", 9:"980run8"}[a.count]
    if a.action == "rtl":
        rtl_fixture(a.temp, a.phase, tag)
    elif not a.count:
        p.error("zero selects only the reference RTL fixture")
    elif a.action == "prepare":
        prepare(a.count)
    elif a.action == "guard":
        trace = directory(a.temp, a.phase, tag, "cold")
        commands, _ = packet_path(trace, 911, expected_shape=(16, 3) if a.count == 9 else (17, 4))
        replay(a.temp, trace, a.temp/f"nes-{tag}-{a.fault}", "control", commands, 911, a.fault)
    else:
        simulate(a.temp, a.phase, "cold", True, work(a.count), True, tag=tag, edition=966)
