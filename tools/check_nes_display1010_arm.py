"""Run the final M4 observer guards and the established loader and menu gates."""
import argparse
import struct
import tempfile
from pathlib import Path

from check_nes_frame862_arm import TimedProbe, timer_cases
from check_nes_frame900_arm import verify
from check_nes_game478 import UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_HOOK_CODE
from check_nes_menu533 import check
from check_nes_sram897 import check_game_path
from nes_order938 import empty_next_offer
from package_nes_trial704 import checked, save
from package_nes_trial855 import loader
from prepare_nes_display1010_arm import PROBE


def check_header(src):
    m=TimedProbe(src)
    target=m.data['ptrcache']+16
    count=0
    def spi(cpu,pc,size,_):
        nonlocal count
        tx=cpu.reg_read(UC_ARM_REG_R1)
        assert 0x20000000<=tx<0x20010000 and bytes(cpu.mem_read(tx,2))==b'\x78\0'
        assert cpu.reg_read(UC_ARM_REG_R3)==32
        count+=1
        cpu.mem_write(cpu.reg_read(UC_ARM_REG_R2),bytes(response))
        m.ret(cpu,int(ok))
    pc=m.syms['nes_native165_bulk']
    m.u.hook_add(UC_HOOK_CODE,spi,None,begin=pc,end=pc)
    gen,token=0x3841,0x89abcdef
    for name in ('match','empty','stale-generation','stale-token','unexpected-chunk','missing-chunk',
                 'collision','partial','interrupted','old-format','SPI-error','reset'):
        row=bytearray(60);struct.pack_into('<H',row,2,gen);row[14]=3
        row[48]=int(name not in ('empty','unexpected-chunk'));struct.pack_into('<I',row,56,token)
        m.u.mem_write(target,bytes(row));m.u.mem_write(m.data['pending950'],struct.pack('<I',target))
        response=bytearray(32);response[1]=0x95 if name=='old-format' else 0xa1
        response[5]=int(name not in ('empty','missing-chunk'))
        struct.pack_into('<H',response,2,gen-(name=='stale-generation'))
        struct.pack_into('<I',response,12,token-(name=='stale-token'))
        response[30]=31 if name=='collision' else 3 if name=='partial' else 15
        response[31]=0 if name=='interrupted' else 0xa5
        ok=name!='SPI-error';before=count
        if name=='reset':m.call('nes_budget210_reset',[])
        m.call('finish_header950',[]);m.call('finish_header950',[])
        assert count==before+(name!='reset'),name
        if name!='reset':
            assert m.u.mem_read(target+14,1)[0]==(7 if name in ('match','empty') else 3),name
            assert bytes(m.u.mem_read(target+48,12))==row[48:],name
    return count


def run(game):
    src=PROBE/'src';out=PROBE.parent/'proof';out.mkdir(exist_ok=True)
    print('PASS1010 ARM row/identity/SRAM',check_header(src),flush=True)
    verify(1010,src,out,marker_values=(4,8,16,24))
    save(out/'timer.json',timer_cases(src))
    save(out/'menu.json',check(src,'1010'))
    cases,ram,entry=check_game_path(src,order=empty_next_offer)
    save(out/'sram.json',dict(cases=cases,ram=ram,entry=entry))
    loader(game,src,1010,out)
    recovery=Path(tempfile.mkdtemp(prefix='recovery-',dir=out))
    checked('check_nes_transfer512_recovery.py',['--arm',src,'--trial',1010,'--fault','none','--out',recovery/'base'],recovery/'base.log')
    print('PASS1010 ARM timer, menu, SRAM, loader CRC, STOP and base')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('game',type=Path)
    run(p.parse_args().game)
