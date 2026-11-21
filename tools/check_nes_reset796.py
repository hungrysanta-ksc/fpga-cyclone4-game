"""Replay the shipped M4 START/reset/boot/STOP path with driven GPIO and SPI responses."""
import json
import struct
from pathlib import Path

from check_nes_game478 import (ELFFile, Uc, UC_ARCH_ARM, UC_MODE_MCLASS, UC_MODE_THUMB,
                               UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                               UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
                               crc, sha)
from check_nes_shared794 import PROBES
from unicorn import UC_HOOK_MEM_WRITE


def replay(src, release_ms, fault=None, control=False, probe=0, *, stopped_pages=None, retained_context=None,
           pre_snapshots=None, deny_release=False, bad_post_crc=False, game=None):
    obj = src / "obj-nes-100"
    firmware = (obj / "firmware.stm").read_bytes()
    u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    for base,size in ((0x08000000,0x40000),(0x20000000,0x10000),
                      (0xe000e000,0x1000),(0x42408000,0x1000)):
        u.mem_map(base,size)
    ready = 0x42408220  # GPIOB IDR bit 8 in the peripheral bit-band
    u.mem_write(ready,struct.pack("<I",1))
    with (obj/"sd2snes.elf").open("rb") as f:
        elf = ELFFile(f)
        symbols = {s.name:s["st_value"] for s in elf.get_section_by_name(".symtab").iter_symbols()}
        for p in elf.iter_segments():
            if p["p_type"]=="PT_LOAD" and p["p_filesz"]:
                at=p["p_paddr"]-0x0800c000
                assert firmware[at:at+p["p_filesz"]]==p.data()
                u.mem_write(p["p_vaddr"],p.data())
    u.mem_write(symbols["phase094"],b"\x02")  # armed after verified readback
    driven = True
    failed = False
    ms = frames = observes = 0
    status = 0x82
    ops, checkpoints, stages, records = [], [], [], []
    pre_reads=0
    reset_releases=[]
    if "nes_boot_probe798" in symbols:
        u.mem_write(symbols["nes_boot_probe798"],bytes([probe]))
    def hook(cpu, address, size, name):
        nonlocal driven, failed, ms, status, frames, observes, pre_reads
        a,b,c = [cpu.reg_read(reg) for reg in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
        value = 0
        if name=="get_snes_reset":
            value = driven or ms<release_ms
        elif name=="snes_reset":
            driven = bool(a)
            if not driven:
                reset_releases.append(pre_reads)
        elif name=="nes_return_delay":
            assert (a,b)==(1,1)
            ms+=1
            value = fault!="timer"
        elif name=="fpga_get_done":
            value = not (fault=="done" and ms>=1)
        elif name=="nes_diag_active":
            value = 1
        elif name=="nes_return_failed":
            value = failed
        elif name=="nes_return_fail":
            failed = True
        elif name=="nes_checkpoint112":
            assert driven and status!=0x86
            checkpoints.append(bytes(cpu.mem_read(a,32)).split(b"\0")[0].decode())
            records.append([checkpoints[-1],b,c])
            value=1
        elif name=="nes_rom_spi_transfer":
            op=cpu.mem_read(b,1)[0]
            ops.append(op)
            reply=bytearray(8)
            if op==0x65:
                reply[1:7]=bytes([0x7b,status,0,6,0,0])
            elif op==0x63:
                assert driven and status==0x82
                status=0x86 if fault!="start" else 0x82
            elif op==0x64:
                assert driven and status==0x86
                status=0x02 if fault!="stop" else 0x86
            elif op==0x70:
                if status==0x86:
                    observes+=1
                reply[1:4]=bytes([0xe5,int(status==2),0])
                if stopped_pages is not None and status==2:
                    reply[2:4]=bytes([3,2])
                reply[4:]=max(1,observes).to_bytes(4,"big")
            elif op==0x73:
                if pre_snapshots is not None and driven and status==0x86:
                    reply[1:]=pre_snapshots[pre_reads]
                    pre_reads+=1
                else:
                    reply[1:]=bytes([0xe6,0xe1 if fault=="copy" else 3,0,0,0,0,3])
            elif stopped_pages is not None and op in stopped_pages:
                assert status==2 and driven
                reply[1:]=stopped_pages[op]
            else:
                assert op in (0x76,0x77)
            cpu.mem_write(c,bytes(reply))
            value=1
        elif name=="nes_native165_bulk" and game is not None and frames:
            return  # Use the real SPI/DMA driver and the modeled DMA registers.
        elif name=="nes_native165_bulk":
            assert cpu.mem_read(b,1)[0]==0xe0
            reply=bytearray(20)
            if fault!="defer" or not driven:
                reply[1]=0xf7
                reply[19]=crc(reply[1:19],8,7,0)
                if bad_post_crc and not driven:
                    reply[19]^=1
            cpu.mem_write(c,bytes(reply))
            value=1
        elif name.startswith("native_frames222"):
            assert not driven and ms>=release_ms and status==0x86
            frames+=1
            if game is not None:
                return  # Execute the linked function with its real caller and stack.
            # Model the next successful periodic observer sample inside gameplay.
            observes+=1
            cpu.mem_write(symbols["nes_run136"]+4,struct.pack("<I",observes))
            if stopped_pages is not None:
                base=symbols["nes_run136"]
                cpu.mem_write(base+20,bytes([4]))
                if retained_context is not None:
                    cpu.mem_write(base+12,struct.pack("<II",retained_context>>32,retained_context&0xffffffff))
                    cpu.mem_write(base+22,bytes([1]))
        cpu.reg_write(UC_ARM_REG_R0,int(value))
        cpu.reg_write(UC_ARM_REG_PC,cpu.reg_read(UC_ARM_REG_LR))
    names=["get_snes_reset","snes_reset","nes_return_delay","fpga_get_done","nes_diag_active",
           "nes_return_failed","nes_return_fail","nes_return_log_allowed","nes_rom_spi_transfer",
           "nes_checkpoint112","nes_native165_bulk",next(n for n in symbols if n.startswith("native_frames222"))]
    for name in names:
        addr=symbols[name]&~1
        u.hook_add(UC_HOOK_CODE,hook,name,begin=addr,end=addr)
    if not control and "nes_boot_stage796" in symbols:
        at=symbols["nes_boot_stage796"]
        u.hook_add(UC_HOOK_MEM_WRITE,lambda cpu,access,address,size,value,data: stages.append(value),
                   begin=at,end=at)
    args=(0x2000b000, 0x60000, 0x2000b080, 1)
    if game is not None:
        args=game.install(u,symbols)
    for reg,val in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):
        u.reg_write(reg,val)
    end=0x0803fff0
    u.reg_write(UC_ARM_REG_SP,0x2000fe00 if game is None else game.entry_sp)
    u.reg_write(UC_ARM_REG_LR,end|1)
    u.emu_start(symbols["nes_display_enter146" if control else "run136"]|1,end,
                count=500000 if game is None else 20000000)
    assert u.reg_read(UC_ARM_REG_PC)==end
    result=u.reg_read(UC_ARM_REG_R0)
    if control:
        assert failed==(release_ms>1) and result==(release_ms<=1)
    else:
        fatal=fault in ("done","timer","start","stop")
        entered=not probe and not deny_release and not bad_post_crc and release_ms<=20 and fault not in ("done","timer","start","copy")
        assert failed==fatal and bool(result)==(not fatal) and frames==int(entered)
        assert ops.count(0x63)==1 and ops.count(0x64)==int(fault not in ("timer","done","start"))
        end_record="PROBE_STOPPED" if probe else "DISPLAY_STOPPED"
        assert checkpoints==(["DISPLAY_NEXT"] if fatal else ["DISPLAY_NEXT",end_record])
        assert driven and ms==(0 if fault=="start" or probe==1 or deny_release else 1 if fault in ("done","timer") else min(20,max(1,release_ms)))
        if not fatal:
            pages=[] if stopped_pages is None else ([0x71,0x72] if retained_context is None else [])+[0x74,0x75]
            suffix=[0x70,0x70,0x73,*pages,0x77,0x76]
            assert ops[-len(suffix):]==suffix and status==2
            expected_error=9 if probe!=1 and release_ms>20 else 6 if fault=="copy" else 0
            if deny_release or bad_post_crc:
                expected_error=7 if deny_release else 8
            if stopped_pages is not None:
                expected_error=4
            if game is not None:
                expected_error=game.expected_error
            assert u.mem_read(symbols["nes_run136"]+20,1)[0]==expected_error
            if probe:
                assert records==[["DISPLAY_NEXT",probe,0x60000],[end_record,probe,expected_error]]
        if frames and "nes_boot_stage796" in symbols:
            assert all(stage in stages for stage in range(1,8))
    report=symbols["nes_run136"]
    def pair(offset):
        hi,lo=struct.unpack("<II",u.mem_read(report+offset,8))
        return f"{hi:08x}{lo:08x}"
    captured={} if stopped_pages is None else dict(context=pair(12),ppu=pair(24),
                        status=list(u.mem_read(report+20,3)),ppu_valid=u.mem_read(report+32,1)[0])
    if pre_snapshots is not None:
        assert pre_reads==len(pre_snapshots)
        assert reset_releases==([] if deny_release else [pre_reads])
        captured.update(pre_reads=pre_reads,reset_releases=reset_releases)
    return dict(**captured,release_ms=release_ms,fault=fault,elapsed_ms=ms,terminal=failed,frame_entry=frames,
                reset_asserted=driven,spi=ops,stages=stages,checkpoints=checkpoints,records=records)


if __name__=="__main__":
    out=PROBES/"nes-reset796"
    old=PROBES/"nes-trial792/link792/src"
    proof={"792":[replay(old,n,control=True) for n in (1,2,20)]}
    for n in (796,797):
        src=out/f"final{n}/src"
        cases=[(v,None) for v in (1,2,19,20,21)]+[(2,f) for f in ("timer","done","defer","copy","start","stop")]
        proof[n]=dict(firmware=sha(src/"obj-nes-100/firmware.stm"),cases=[replay(src,v,f) for v,f in cases])
    (out/"handoff.json").write_text(json.dumps(proof,indent=2)+"\n")
    print("PASS: 3 previous reset samples, 22 final linked startup/STOP cases")
