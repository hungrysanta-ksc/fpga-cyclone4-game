"""Exercise the final STM builds, including RUN past the old timer and wrap."""
import json
import struct
from pathlib import Path
import check_carts1056 as old
from check_ff3_sd1043 import Machine, fat16, crc8, UC_HOOK_CODE, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_XPSR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
from prepare_cart_stage1057 import BASE, OUT


def long_run():
    m = Machine(OUT / "release/link/src", fat16())
    u = m.u
    # Allocate the same caller-owned buffers separately, with ample spacing.
    b = 0x20010000
    u.mem_map(b, 0x20000)
    s = m.sym["native_runtime165"]
    tick, callback, status = 0x0807fa01, 0x0807fa11, b+0x1f000
    u.mem_write(tick-1, bytes.fromhex("00687047"))  # return *ctx
    u.mem_write(callback-1, bytes.fromhex("01207047"))
    transfer=callback+16
    u.mem_write(transfer-1,bytes.fromhex("01207047"))
    def status_reply(cpu,pc,size,user):
        assert cpu.reg_read(UC_ARM_REG_R3)==20 and bytes(cpu.mem_read(cpu.reg_read(UC_ARM_REG_R1),1))==b'\xe0'
        reply=bytearray(20)
        reply[1]=0xf7
        reply[-1]=crc8(reply[1:-1])
        cpu.mem_write(cpu.reg_read(UC_ARM_REG_R2),bytes(reply))
    u.hook_add(UC_HOOK_CODE,status_reply,None,transfer-1,transfer-1)
    sp = m.sym["__stack"]-64
    u.mem_write(sp, struct.pack("<8I",transfer,tick,callback,status,0,b+0x10000,1,1))
    for r,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),(s,b,b+0x8000,b+0x1e000)):
        u.reg_write(r,v)
    end=0x0807fff0
    u.reg_write(UC_ARM_REG_SP,sp)
    u.reg_write(UC_ARM_REG_XPSR,0x01000000)
    u.reg_write(UC_ARM_REG_LR,end|1)
    u.emu_start(m.sym["nes_runtime165_begin"]|1,end,count=1000000)
    assert (u.reg_read(UC_ARM_REG_PC),u.reg_read(UC_ARM_REG_R0))==(end,1), (hex(u.reg_read(UC_ARM_REG_PC)),u.reg_read(UC_ARM_REG_R0))
    for ticks in (5999,6000,6001,360000,0x7fffffff,0xffffffff,0):
        u.mem_write(status,struct.pack("<I",ticks))
        assert m.call("guard",s)==1
    u.mem_write(callback-1,bytes.fromhex("00207047"))
    u.ctl_remove_cache(callback-1,callback+3)
    assert m.call("guard",s)==0


def reset_exit():
    m=Machine(OUT/"release/link/src",fat16())
    u=m.u
    u.mem_map(0xe000e000,4096)  # USB IRQ disabled
    u.mem_map(0x42408000,4096)  # GPIOB IDR bit 8, MCU ready
    u.mem_write(0x42408220,struct.pack("<I",1))
    u.mem_write(m.sym["phase094"],b"\x04")
    u.mem_write(m.sym["nes_allow_cart_reset1057"],b"\x01")
    pressed=False
    asserted=False
    def pins(cpu,pc,size,name):
        nonlocal asserted
        value=0
        if name=="get_snes_reset":value=int(pressed or asserted)
        elif name=="snes_reset":
            assert cpu.reg_read(UC_ARM_REG_R0)==1
            asserted=True
        elif name in ("nes_diag_active","fpga_get_done"):value=1
        cpu.reg_write(UC_ARM_REG_R0,value)
        cpu.reg_write(UC_ARM_REG_PC,cpu.reg_read(UC_ARM_REG_LR))
    for name in ("get_snes_reset","snes_reset","nes_diag_active","fpga_get_done","nes_return_log_allowed","nes_return_failed"):
        pc=m.sym[name]&~1
        u.hook_add(UC_HOOK_CODE,pins,name,pc,pc)
    assert m.call("nes_cf86_check094")==1 and not asserted
    pressed=True
    assert m.call("native_service165",0)==0 and asserted
    pressed=False
    assert m.call("nes_cf86_check094")==1 and m.call("nes_display_leave146")==1
    assert u.mem_read(m.sym["phase094"],1)[0]==2


if __name__=="__main__":
    ref=json.loads((BASE/"reference.json").read_text())
    old.OUT=OUT
    proof={p:old.headers(p,ref) for p in ("debug","release")}
    long_run()
    reset_exit()
    old.check(Path.home()/"Downloads/test")
    proof["battery_roundtrip_bytes"]=old.battery()
    proof["release_timer"]="60 s, one hour, 32-bit wrap, service cancellation"
    (OUT/"guards.json").write_text(json.dumps(proof,indent=2))
