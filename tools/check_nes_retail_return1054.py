"""Execute the release menu/run/STOP path, with physical devices and play emulated."""
import json
import struct
from pathlib import Path
from check_nes_pair1054 import Machine, WORK, drive, UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_PC, UC_ARM_REG_LR
from check_ff3_sd1043 import crc8

def run(board, root=WORK, retry_delays=None, menu_timeout=False, raw=None, image=None, reject_crc=False, expected_prg_bytes=None):
    if raw is None:
        raw=next((Path.home()/'Downloads/test').glob('Hoshi no Kirby*.nes' if board==0x7c else 'Final Fantasy III*rel.DWYN*.nes')).read_bytes()
    prg=raw[4]*16384 if expected_prg_bytes is None else expected_prg_bytes
    if image is None:image='/sd2snes/nes-chr'+('rom' if board==0x7c else 'ram')+'.bi3'
    m=Machine(root/'release/link/src',drive(raw))
    u=m.u
    u.mem_map(0xe000e000,4096)
    u.mem_map(0x40013000,4096)
    u.mem_write(0x40013008,struct.pack('<I',2))
    u.mem_write(m.sym['gpio_owned'],b'\0')
    path=0x0807fc00
    u.mem_write(path,b'0:/test.nes\0')
    assert m.call('nes_menu_select_rom',path)==1
    total=len(raw)-16
    flags=count=0
    configs=[]
    sequence=[]
    pages=[]
    revised='nes_menu_blank1054' in m.sym
    messages=[]
    menu_commands=[]
    events=[]
    probes=0

    def device(u,pc,size,name):
        nonlocal flags,count,probes
        a,b,c=(u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2))
        result=1
        if name=='snes_set_snes_cmd':
            menu_commands.append(a)
        elif name=='snes_get_mcu_cmd':
            if menu_timeout:
                tick=struct.unpack('<I',u.mem_read(m.sym['ticks'],4))[0]
                u.mem_write(m.sym['ticks'],struct.pack('<I',tick+20))
                result=0
            else:
                result={0x55:0x0b,0x77:0x80}[menu_commands[-1]]
        elif name=='delay_ms':
            events.append(('delay',a))
        elif name=='snes_reset':
            events.append(('reset',a))
        elif name=='snes_bootprint_center':
            u.mem_write(m.sym['snes_boot_configured'],struct.pack('<I',1))
            fmt=bytes(u.mem_read(b,32)).split(b'\0')[0].decode()
            messages.append((a,fmt,c))
            if fmt=='Starting NES':events.append(('starting',0))
        elif name=='retail_write_page1054':
            assert c==512 and b not in pages
            off=len(pages)*512
            block=raw[16+off:16+off+512]
            if off>=prg:
                block=bytes(block[j//16*16+(j&1)*8+(j%16)//2] for j in range(512))
            assert bytes(u.mem_read(a,512))==block
            assert b==(off if off<prg else 0x200000+off-prg)
            pages.append(b)
        elif name=='slow_begin':u.mem_write(m.sym['gpio_owned'],b'\1')
        elif name=='slow_end':u.mem_write(m.sym['gpio_owned'],b'\0')
        elif name=='nes_diag_fpga_pgm':
            configs.append(bytes(u.mem_read(a,80)).split(b'\0')[0].decode())
        elif name=='fpga_test':result=0xa5
        elif name.startswith('native_session165'):
            u.mem_write(m.sym['nes_run136'],struct.pack('<II',20,40))
        elif name=='nes_game149_transfer':
            tx=bytes(u.mem_read(b,8))
            op=tx[0];rx=bytearray(8)
            if 0x60<=op<=0x65:
                assert tx[4]^tx[5]==255 and crc8(tx[:6])==tx[6] and tx[7]==0xa5
                address=int.from_bytes(tx[1:4],'big')
                if op!=0x65:sequence.append(op)
                if op==0x60:
                    assert tx[4]==3 and not count and address==0
                    count=total
                elif op==0x62:
                    assert count==address==total and not flags
                    flags=0x82
                elif op==0x63:
                    assert flags==0x82 and address==total
                    flags=0x86
                elif op==0x64:
                    assert flags==0x86 and address==total and not tx[4]
                    flags=2
                else:assert op==0x65
                rx[1]=board;rx[2]=flags;
                if retry_delays is not None and op==0x65 and not count:
                    probes+=1
                    if probes<=retry_delays:rx[1]=0
                rx[4:7]=count.to_bytes(3,'big')
            elif op==0x70:
                rx[1]=0xe5;rx[2]=1;rx[4:8]=(50 if flags==2 else 0).to_bytes(4,'big')
            elif op==0x73:rx[1]=0xe6;rx[2]=6;rx[6]=1;rx[7]=3
            elif op==0x77:rx[1]=0xe5;rx[5:8]=bytes((1,96,3))
            elif op==0x76:rx[1]=0xe5;rx[7]=1
            else:raise AssertionError(hex(op))
            u.mem_write(c,bytes(rx))
        elif name=='sram_writeblock':pages.append(b)
        u.reg_write(UC_ARM_REG_R0,result)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    names=['snes_reset','nes_diag_sd_handoff113','nes_css_begin108','nes_css_end108',
           'nes_cf86_enter094','nes_cf86_arm094','nes_cf86_check094','nes_cf86_finish094',
           'nes_return_spi_ready','configured','slow_begin','slow_end','nes_diag_fpga_pgm',
           'fpga_test','nes_game149_transfer','snes_bootprint_center','sram_writeblock',
           'nes_diag_observe','nes_display_leave146','nes_restore_boot_battery',
           next(n for n in m.sym if n.startswith('native_session165'))]
    if revised:
        names.extend(['retail_write_page1054','snes_get_mcu_cmd','snes_set_snes_cmd','delay_ms'])
    for name in names:
        addr=m.sym[name]&~1
        u.hook_add(UC_HOOK_CODE,device,name,addr,addr)
    finished=m.call('nes_menu_diagnostic_run',path,instructions=150000000)
    if not revised and retry_delays:
        assert not finished and probes==1 and not sequence
        assert messages[-1][1:] == ('%u%%',100)
        assert configs==['/sd2snes/nes-chrram.bi3']
        return dict(base_restored=False,mutations=sequence,status_probes=probes)
    assert finished
    if reject_crc:
        assert not sequence and not probes and ('starting',0) not in events
        assert configs==['/sd2snes/fpga_base.bi3']
        assert any(fmt=='ROM read failed' for _,fmt,_ in messages)
        assert m.call('nes_menu_diagnostic_prepared',1)==1
        m.call('nes_menu_diagnostic_released')
        assert not m.call('nes_menu_diagnostic_pending') and not m.writes
        return dict(rejected_before_start=True,base=configs[-1])
    if revised:
        assert menu_commands==([0x55] if menu_timeout else [0x55,0x77])
        if menu_timeout or retry_delays>=20:
            assert not sequence and configs[-1]=='/sd2snes/fpga_base.bi3'
            assert m.call('nes_menu_diagnostic_prepared',1)==1
            m.call('nes_menu_diagnostic_released')
            assert not m.call('nes_menu_diagnostic_pending') and not m.writes
            return dict(recovered=True,mutations=sequence,pages=len(pages),status_probes=probes)
        assert probes==retry_delays+1
        assert [c for _,fmt,c in messages if fmt=='%u%%']==list(range(5,100,5))
        assert messages[-2][1]=='100%%'
        pos=events.index(('starting',0))
        assert events[pos+1:pos+4]==[('delay',100),('reset',1),('delay',5)]
    assert sequence==[0x60,0x62,0x63,0x64] and len(pages)==total//512
    assert configs==[image,'/sd2snes/fpga_base.bi3']
    assert m.call('nes_menu_diagnostic_prepared',1)==1
    m.call('nes_menu_diagnostic_released')
    assert m.call('nes_menu_diagnostic_pending')==0 and not m.writes
    return dict(commands=sequence,stage_blocks=len(pages),base=configs[-1],sd_writes=m.writes,menu_released=True)

if __name__=='__main__':
    r={k:run(n) for k,n in [('kirby',0x7c),('ff3',0x7d)]}
    (WORK/'release/return.json').write_text(json.dumps(r,indent=2))
    print(r)
