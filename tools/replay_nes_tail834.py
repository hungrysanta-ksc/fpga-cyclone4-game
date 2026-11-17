"""Observe the target passed to through() and the window seen by each status read."""
import argparse
from pathlib import Path

from check_nes_game478 import ELFFile
from nes_tail834 import OUT, MODES
from nes_repeat833 import OUT as RAW, PROBES, client as build_client
from replay_nes_repeat833 import replay, trace_credit
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R2


def watch(cpu):
    trace_credit(cpu)
    with (cpu.a.arm/"obj-nes-100/sd2snes.elf").open("rb") as f:
        owner=None
        for sym in ELFFile(f).get_section_by_name(".symtab").iter_symbols():
            if sym["st_info"]["type"]=="STT_FILE":
                owner=sym.name
            if owner=="nes_sink_window184.c" and sym.name=="status":
                status=sym["st_value"]&~1
    def target(u,pc,size,ctx):
        cpu.through834=u.reg_read(UC_ARM_REG_R2)&65535
    def snapshot(u,pc,size,ctx):
        if cpu.generation!=909:
            return
        w=u.reg_read(UC_ARM_REG_R0)
        counters=bytes(u.mem_read(w+20,4))
        sent=int.from_bytes(counters[:2],"little")
        retired=int.from_bytes(counters[2:],"little")
        with (cpu.a.out/"window834.txt").open("a") as log:
            print(cpu.clock,sent,retired,getattr(cpu,"through834",-1),file=log)
    through=cpu.syms["nes_window184_through"]&~1
    cpu.u.hook_add(UC_HOOK_CODE,target,begin=through,end=through)
    cpu.u.hook_add(UC_HOOK_CODE,snapshot,begin=status,end=status)


def client_for(kind):
    return RAW/"client" if kind=="original" else OUT/("client-"+kind)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("base","stock",*MODES))
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("temp",type=Path)
    p.add_argument("budget",type=Path)
    p.add_argument("--client",choices=("original","checked","wide","inspect"),default="original")
    p.add_argument("--build-client",action="store_true")
    p.add_argument("--fixed",action="store_true")
    p.add_argument("--fault",choices=("damage","stop","offset"))
    p.add_argument("--repair",action="store_true")
    a=p.parse_args()
    client=client_for(a.client)
    if a.build_client:
        assert a.client!="original"
        build_client(PROBES/"nes-seal831/client",client,
                     expected="c9196b0a59c068e0100cbcc87eeaf1d424628c10c590115893352d404a118ca1",
                     step=16 if a.client in ("wide","inspect") else 8,inspect_first=a.client=="inspect")
    else:
        original=a.mode in ("stock","base")
        link=PROBES/"nes-output823"/(("link-833" if original else "link-834")+a.mode)
        tag="834"+a.mode+a.client+("fixed" if a.fixed else "")+(a.fault or "")+("repair" if a.repair else "")
        replay(a.mode,a.phase,a.temp,a.budget,a.fixed,a.fault,tag,client=client,
               arm=link,overlay_root=RAW if original else OUT,on_attach=watch,force_repair=a.repair)
