# SPDX-License-Identifier: MIT
"""Exercise the positive-credit input callback and its exclusion boundaries."""
import argparse
import json
from pathlib import Path

from check_nes_credit752 import Handoff, sha
from check_nes_idle676 import Receiver


def check(src, policy):
    layouts = Handoff(src, "normal").layout
    cases = []
    for case in ("ready","no_finish","map_drain","already_started","other_section",
                 "other_page","STOP_before","STOP_after_READ","bad_CRC"):
        fault = case in ("STOP_before","STOP_after_READ","bad_CRC")
        cpu = Receiver(src, case if fault else "normal")
        cpu.layout.update({k:layouts[k] for k in ("nes_plan200","nes_sink_window184")})
        rt = cpu.layout["nes_native_runtime165"]
        cpu.put(cpu.rt+rt["plan"],"nes_plan200","finished",int(case!="no_finish"),1)
        credit = 6 if case=="already_started" else 7
        cpu.put(cpu.rt,"nes_native_runtime165","prefetch_left",credit,1)
        # A partially spent budget implies the previous COMMITTED receiver
        # has already been released. Supply one valid next geometry block.
        cpu.put(cpu.state,"nes_native165","state",0,1)
        old = 0x20008000
        cpu.put(cpu.rt,"nes_native_runtime165","resident",old,4)
        cpu.put(old,"nes_resident211","map_upload",(1<<32) | (case=="other_page"),8)
        window = cpu.rt + rt["transport"]
        cpu.u.mem_write(window+layouts["nes_sink_window184"]["last"],bytes([2,2 if case=="other_section" else 5]))
        reason = int(case=="map_drain")
        ok = cpu.call("wait634",[cpu.rt,cpu.check|1,reason,1])
        eligible=(not reason and case!="no_finish" and
                  (policy!="firstfit" or credit==7) and
                  (policy!="headfit" or case!="other_section") and
                  (policy!="page" or case!="other_page"))
        assert bool(ok)==(not fault)
        if eligible and not fault:
            assert cpu.ops==[0xd0,0xd1,0xd2,0xd0] and cpu.index==1
        elif fault:
            assert 0xd2 not in cpu.ops and cpu.index==0
        else:
            assert not cpu.ops and cpu.index==0
        cases.append(dict(case=case,allowed=eligible,result=bool(ok),SPI=cpu.ops))
    return dict(firmware=sha(src/"obj-nes-100/firmware.stm"),cases=cases)


def reproduce_beam(trace, out, mesen, client, generation=957):
    """Replay the recorded packet prefix; keep the original independent guard."""
    import re
    import subprocess
    from types import SimpleNamespace
    from unittest.mock import patch
    import replay_nes_map527 as replay
    from trace_nes_owner739 import observe
    from nes_raw506 import once
    args = SimpleNamespace(trace=trace,out=out,mesen=mesen,client=client,frames=generation-905+1)
    def instrument(script):
        original = "beam685 and beam685.line>=225 and beam685.line<=252 and beam685.frame==st.frameCount"
        return once(script, "assert("+original+")", """assert("""+original+""",
   string.format("g=%d line=%d frame=%d sampled_line=%d sampled_frame=%d cpu_line=%d bytes=%d off=%d clock=%d",word(0x1226),
   st['ppu.scanline'],st.frameCount,beam685 and beam685.line or -1,beam685 and beam685.frame or -1,rd(0x103e),n,off,st.masterClock))""")
    with patch.object(replay,"observe",observe):
        try:
            replay.run(args,edit_script=instrument)
        except subprocess.CalledProcessError:
            pass
    message=(out/"map-error.txt").read_text()
    fields={name:int(value) for name,value in re.findall(r"(\w+)=(-?\d+)",message)}
    assert fields["g"]==generation and not (225<=fields["sampled_line"]<=252 and fields["sampled_frame"]==fields["frame"])
    from analyze_nes_output768 import csv_groups
    def prefix(folder):
        return [(g,r["clock"]) for g,rows in csv_groups(folder/"window.csv").items()
                for r in rows if r["op"]==3 and r["event"]=="reveal"]
    assert prefix(trace)==prefix(out) and prefix(out)[-1][0]==generation-1
    (out/"beam.json").write_text(json.dumps(fields,indent=2)+"\n",newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    import sys
    if sys.argv[1:2]==["beam"]:
        for key in ("trace","out","mesen","client"):
            p.add_argument(key,type=Path)
        p.add_argument("--generation",type=int,default=957)
        a=p.parse_args(sys.argv[2:])
        reproduce_beam(a.trace,a.out,a.mesen,a.client,a.generation)
        raise SystemExit(0)
    p.add_argument("src",type=Path)
    p.add_argument("policy",choices=("credit","firstfit","headfit","page"))
    p.add_argument("out",type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(check(a.src,a.policy),indent=2)+"\n",newline="\n")
