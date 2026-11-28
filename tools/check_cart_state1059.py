"""Physical 1058 captures and 1059 linked FAT/ARM save across a card restart."""
import json
import re
import struct
from pathlib import Path
from statistics import median
from check_ff3_sd1043 import Machine, fat16
import check_carts1056 as cart
from prepare_cart_state1059 import BASE, OUT


def traces():
    result={}
    for frame in (Path.home()/"Downloads").glob("nes-frame-debug1058-*.bin"):
        data=frame.read_bytes()
        magic,edition,_,count,_,_,stride,_=struct.unpack_from("<8H",data)
        assert (magic,edition,stride)==(0x9001,1058,60) and count<=80
        text=frame.with_name(frame.name.replace("frame","game-last")).with_suffix(".txt").read_text()
        rec=dict(re.findall(r"(\w+)=([\w]+)",text))
        assert all(rec[k]=="1" for k in ("start","stop","base")) and rec["rom"]==rec["err"]=="0"
        progress=frame.with_name(frame.name.replace("frame","progress")).with_suffix(".txt").read_bytes()
        stop=frame.with_name(frame.name.replace("frame","stop")).read_bytes()
        tail=[]
        for i in range(count):
            r=struct.unpack_from("<6H4B",data,16+i*stride)
            if r[0]>=5500 and r[8]&3==3:tail.append(r)
        result[rec["id"]]=dict(opening=int(rec["w1"]),demo=int(rec["w2"]),displayed55=struct.unpack_from("<H",data,4816)[0],
            ack_samples=len(tail),no_map_dirty=sum(r[7]==0 for r in tail),
            input_to_ack_ms=round(median((r[3]-r[4])*512/84000 for r in tail),2) if tail else None,
            progress_bytes=len(progress),stop_bytes=len(stop))
    assert result.keys()=={"82","83","84"}
    return result


def state(board,crc,rom_size,size,root=None):
    disk=fat16()
    def boot():
        machine=Machine((root or OUT)/"release/link/src",disk)
        from unicorn import UC_HOOK_CODE
        from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_LR
        delay=machine.sym["delay_us"] & ~1
        machine.u.hook_add(UC_HOOK_CODE,lambda u,*_: u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR)),None,delay,delay)
        machine.rom(crc)
        machine.u.mem_write(machine.sym["nes_board_id"],bytes([board]))
        machine.u.mem_write(machine.sym["nes_cart_bytes"],struct.pack("<I",rom_size))
        machine.state=bytearray(size)
        return machine
    payload=bytearray((i*31+(i>>8))&255 for i in range(size))
    payload[:8]=struct.pack("<II",0,size//4)
    payload[14]&=252
    m=boot()
    m.state[:]=payload
    assert m.call("nes_menu_state_io",1,0,live=True)==1 and m.writes>0
    assert m.call("nes_menu_state_resume")==1
    if board in (0x83,0x84,0x85):
        battery=bytes((i*11+i//128)&255 for i in range(8192))
        m.battery[:]=battery
        assert m.call("nes_menu_state_io",0,0,live=True)==1
        m=boot()
        assert m.call("nes_restore_boot_battery",instructions=180000000)==1
        assert m.flags==0 and m.battery==battery and not m.writes
    else:
        assert m.call("nes_menu_state_io",0,0,live=True)==0xffffffff
    m=boot()
    m.u.mem_write(m.sym["ff3_next_slot"],b"\1")
    assert m.call("nes_restore_boot_battery",instructions=180000000)==1
    assert m.flags==0 and m.state==payload and not m.writes
    m.rom(crc^1)
    assert m.call("nes_menu_state_io",1,1,live=True)==0
    return size


if __name__=="__main__":
    import sys
    if "vrc" in sys.argv: OUT=OUT/"vrc"
    cart.OUT=OUT
    result=dict(physical=traces())
    ref=json.loads((BASE.parent/"nes-carts1056/reference.json").read_text())
    result["header"]={name:cart.headers(name,ref) for name in ("debug","release")}
    if "vrc" in sys.argv: result["vrc_state"]=state(0x83,0x20f150ff,0x60000,21264)
    result["states"]=[state(0x82,0xca40be7e,0x80000,21264),state(0x84,0x9ac62bb9,0x100000,22280)]
    result["battery"]=cart.battery()
    import check_cart_stage1057 as stage
    stage.OUT=OUT
    stage.long_run()
    stage.reset_exit()
    result["release_guard"]="timer wrap and reset exit"
    cart.check(Path.home()/"Downloads/test")
    (OUT/"checks.json").write_text(json.dumps(result,indent=2))
    print(result)
