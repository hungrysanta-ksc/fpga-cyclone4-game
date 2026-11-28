"""Recheck the final ARM links, their SD menu image and the stair geometry."""
import argparse
import hashlib
import json
import os
import struct
import subprocess
import tempfile
import zipfile
import zlib
from pathlib import Path

import check_nes_retail1054r2 as retail
from build_nes_game164 import RGB
from check_ff3_backdrop1046 import captured, check
from check_ff3_menu_arm import Player, dispatch, verify_slots
from check_ff3_menu_cpu import run_case
from check_nes_pair1054 import (Machine, drive, UC_HOOK_CODE, UC_ARM_REG_R0,
                                UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_PC, UC_ARM_REG_LR)
from check_nes_retail_return1054 import run
from prepare_ff3_pair1055 import OUT, ROOT


def client_pixels(mesen, cases):
    client=OUT.parent/'nes-ff3-1050/client'
    cart=bytearray((client/'sink165.sfc').read_bytes())
    jump=bytes.fromhex('5c 00 20 7e')
    assert cart.count(jump)==1
    cart[cart.index(jump):cart.index(jump)+4]=bytes.fromhex('5c 00 a0 00')
    cart[0x2000:0x2004]=bytes.fromhex('5c 00 1a 7e')
    raw=json.loads((client/'labels.json').read_text())['raw_dma489']&65535
    with tempfile.TemporaryDirectory(prefix='nes-1055-') as tmp:
        d=Path(tmp)
        (d/'test.sfc').write_bytes(cart)
        (d/'cases').write_bytes(b''.join(bytes([len(c)//256])+c for c in cases))
        lua=(ROOT/'tests/nes-functional/ff3_raw1050.lua').read_text()
        (d/'test.lua').write_text(lua.replace('@ROOT@',json.dumps(d.as_posix())).replace('@RAW@',str(raw)).replace('@FILL@','255'))
        subprocess.run([mesen,'--testRunner',d/'test.lua',d/'test.sfc','--timeout=45',
                        '--doNotSaveSettings','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,
                       capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True,timeout=60,
                       env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'))
        total=sum(map(len,cases))*2
        result=(d/'result').read_text()
        assert result==f'PASS {total} 0',(result,total)
    for command in ('resume','load','exit'):
        run_case(client,mesen,command)
    return total


def copy_menu(src, image, damage):
    m=Machine(src,drive(image))
    u=m.u
    base=0xc00000
    physical=bytearray(len(image))
    totals={'write':0,'read':0}

    def port(u,pc,size,write):
        ptr,address,count=(u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2))
        i=address-base
        direction='write' if write else 'read'
        assert i==totals[direction] and count==256
        if write:
            physical[i:i+count]=u.mem_read(ptr,count)
        else:
            if damage and i==32768:physical[i+31]^=1
            u.mem_write(ptr,bytes(physical[i:i+count]))
        totals[direction]+=count
        u.reg_write(UC_ARM_REG_R0,1 if write else count)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))

    for name,write in [('retail_write_page1054',True),('sram_readblock',False)]:
        pc=m.sym[name]&~1
        u.hook_add(UC_HOOK_CODE,port,write,pc,pc)
    path=0x0807fc00
    u.mem_write(path,b'0:/test.nes\0')
    m.call('nes_return_io_begin')
    n=m.call('nes_return_copy_menu',path,base,0)
    assert n==(0 if damage else len(image)) and bool(m.call('nes_return_failed'))==damage
    assert totals['write']==totals['read']==(33024 if damage else len(image)) and not m.writes
    return totals['read']

def reset_return(src,settle_ms):
    m=Machine(src,drive(bytes(512)))
    u=m.u
    phase=m.sym['phase094']
    u.mem_write(phase,b'\x04')  # DISPLAY146
    requested=False
    elapsed=0
    def pins(u,pc,size,name):
        nonlocal requested,elapsed
        asserted=requested and elapsed>=settle_ms
        state=u.mem_read(phase,1)[0]
        result=1
        if name=='snes_reset':
            assert u.reg_read(UC_ARM_REG_R0)==1
            requested=True
        elif name=='get_snes_reset':result=int(asserted)
        elif name=='nes_cf86_check094':
            result=int(state==3 or (state==4 and not asserted) or (state==2 and asserted))
        elif name=='nes_return_delay':
            assert requested and state==3 and u.reg_read(UC_ARM_REG_R0)==1
            elapsed+=1
        else:
            assert name=='nes_cf86_fail094'
            u.mem_write(phase,b'\x05')
            result=0
        u.reg_write(UC_ARM_REG_R0,result)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    for name in ('snes_reset','get_snes_reset','nes_cf86_check094','nes_return_delay','nes_cf86_fail094'):
        pc=m.sym[name]&~1
        u.hook_add(UC_HOOK_CODE,pins,name,pc,pc)
    return [m.call('nes_display_leave146'),elapsed]


def verify(slot,mesen):
    data=slot.read_bytes()
    crc=0x4be84aa7
    assert struct.unpack_from('<4s6I',data)==(b'NESS',1,crc,524288,1,21264,15)
    assert struct.unpack_from('<II',data,28)==(zlib.crc32(data[36:]),zlib.crc32(data[:32]))
    records=[entry for first in (55,95,134,218) for entry in captured(OUT/f'g{first}'/f'{first}.log')]
    assert len(records)==16
    # Compare every originally composed scanline to the reference ROM image.
    patterns={}
    cases=[]
    for frame,(_,_,rasters,_,_,palette,pixels) in records:
        rgb=(OUT/'tower'/f'frame-{frame:04}.rgb').read_bytes()
        lines=[y for y,r in enumerate(rasters) if r>>49&1]
        uniform=0
        retained=bytearray()
        for slot_id,y in enumerate(lines):
            original=pixels[slot_id*256:(slot_id+1)*256]
            assert b''.join(bytes.fromhex(RGB[c]) for c in original)==rgb[(y+8)*768:(y+9)*768],(frame,y)
            if all(c==palette[0] for c in original):
                uniform+=1
            else:
                retained.extend(original)
        assert len(retained)==256
        cases.append(bytes(retained))
        patterns[frame]=[len(lines),uniform]
    profiles={}
    for name in ('release','debug'):
        src=OUT/name/'link/src'
        check(src,[],records,fold_backdrop=True)
        profiles[name]=dispatch(src,crc,data[36:])
        profiles[name]['firmware_sha256']=hashlib.sha256((src/'obj-nes-100/firmware.stm').read_bytes()).hexdigest()
        profiles[name]['distinct_slots_reloaded']=verify_slots(src,data[36:])
        m=Player(src,drive(bytes(512)),crc)
        m.command(1);m.command(7)
        assert not m.writes
    release=OUT/'release/link/src'
    previous=OUT.parent/'nes-pair1054r2/NES-1054r2-RELEASE-SD-ROOT.zip'
    with zipfile.ZipFile(previous) as z:image=z.read('sd2snes/m3nu.bin')
    retail.OUT=OUT
    reset=[reset_return(OUT.parent/'nes-pair1054r2/release/link/src',3)]
    reset.extend(reset_return(release,ms) for ms in (0,3,25))
    assert reset==[[0,0],[1,0],[1,3],[0,20]],reset
    report=dict(stair_input_and_solid_rows=patterns,profiles=profiles,actual_raw_dma_pixels=client_pixels(mesen,cases),
                reset_return_old_3ms_new_0_3_25ms=reset,
                menu_copy=copy_menu(release,image,False),menu_corrupt_stop_at=copy_menu(release,image,True),
                copy_ready=retail.write_page(),injected_unready=retail.write_page(17),
                ff3_stop_base=run(0x7d,OUT,1))
    (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('slot',type=Path)
    parser.add_argument('mesen',type=Path)
    a=parser.parse_args()
    print(verify(a.slot,a.mesen))
