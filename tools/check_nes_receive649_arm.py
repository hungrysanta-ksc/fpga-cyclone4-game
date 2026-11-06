"""Check the real early receive callback, failure propagation and shared seven-block cap."""
import argparse
import json
from pathlib import Path
from nes_raw506 import encode,sha
from test_nes_prefetch498_arm import Probe


def check(src,data,mode,fault):
    g=(data/"frame951.geometry").read_bytes()
    raw=(data/"frame951.raw").read_bytes()
    m=Probe(src,g,raw,fault)
    m.packets,_,_=encode(g,raw,951)
    m.put(m.video,"nes_native_video165","generation",950,2)
    plan=m.rt+m.layout["nes_native_runtime165"]["plan"]
    guard=m.get(m.w,"nes_sink_window184","guard",4)
    def wait(reason,progress=False):
        return m.call("wait634",[m.rt,guard,reason,int(progress)])
    if mode=="credit":
        assert wait(0) and not m.input_calls
        m.put(plan,"nes_plan200","finished",1,1)
        m.put(m.w,"nes_sink_window184","sent",1,2)
        assert wait(0,True) and not m.input_calls
        m.put(m.w,"nes_sink_window184","retired",65535,2)
        reason=0
    else:
        if mode=="sealed":
            assert wait(4) and not m.input_calls
        reason=4 if mode=="stream" else 3
    ok=wait(reason)
    if fault!="none":
        assert not ok and m.get(m.rt,"nes_native_runtime165","result") and m.index<=1
        assert not wait(2) and m.input_calls.count(0xd1)<=1
    else:
        assert ok and m.index==1
        for _ in range(3):
            assert wait(0 if mode=="credit" else 4)
        assert m.index==4
        address=0x2001b000
        m.u.mem_write(address,bytes((0xe1,3))+bytes(17))
        m.syms["aliased_E1"]=m.get(m.w,"nes_sink_window184","transfer",4)&~1
        assert m.call("aliased_E1",[m.rt,address,address,19])
        assert m.get(m.rt,"nes_native_runtime165","prefetch_left")==3
        for _ in range(6):assert wait(2)
        assert m.index==7 and m.input_calls.count(0xd1)==7 and m.input_calls.count(0xd2)==7
        n=m.get(m.state,"nes_native165","at",2)
        assert n and bytes(m.u.mem_read(m.state+m.layout["nes_native165"]["maps"],2*n))==g[:2*n]
    assert 0xd3 not in m.input_calls and m.get(m.video,"nes_native_video165","generation",2)==950
    return dict(case=fault,pops=m.index,passed=True,successor_commit=False)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("src","data","out"):p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--mode",required=True,choices=("credit","stream","sealed"))
    a=p.parse_args()
    rows=[check(a.src,a.data,a.mode,f) for f in ("none","IO","CRC","service_after_D2","deadline_after_D2")]
    a.out.write_text(json.dumps(dict(firmware=sha(a.src/"obj-nes-100/firmware.stm"),cases=rows),indent=2)+"\n")
