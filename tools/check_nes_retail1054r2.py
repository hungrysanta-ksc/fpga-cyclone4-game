"""Release handoff regression on the linked Cortex-M4 image; model SPI and SD at their boundaries."""
import json
from pathlib import Path
from check_nes_retail_return1054 import run
from check_nes_pair1054 import Machine, drive, UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_PC, UC_ARM_REG_LR
from prepare_nes_retail1054r2 import OUT, WORK


def write_page(stop_at=None):
    raw=next((Path.home()/'Downloads/test').glob('Final Fantasy III*rel.DWYN*.nes')).read_bytes()
    m=Machine(OUT/'release/link/src',drive(raw))
    u=m.u
    u.mem_map(0x40020000,4096)
    payload=raw[-512:]
    u.mem_write(0x0807f400,payload)
    completed=bytearray()
    received=False
    cs=[]
    def spi(u,pc,size,name):
        nonlocal received
        value=u.reg_read(UC_ARM_REG_R0)
        answer=0
        if name=='set_mcu_addr':
            assert value==0x7fe00
        elif name=='spi_tx_byte':
            assert value==0x98 and not completed
            cs.append(value)
        elif name=='spi_txrx_byte':
            assert cs==[0x98] and not received and value==payload[len(completed)]
            received=True
            completed.append(value)
        elif name=='nes_return_spi_ready':
            assert received
            received=False
            answer=int(len(completed)!=stop_at)
        u.reg_write(UC_ARM_REG_R0,answer)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    for name in ('set_mcu_addr','spi_tx_byte','spi_tx_sync','spi_txrx_byte','nes_return_spi_ready'):
        addr=m.sym[name]&~1
        u.hook_add(UC_HOOK_CODE,spi,name,addr,addr)
    result=m.call('retail_write_page1054',0x0807f400,0x7fe00,512)
    assert result==int(stop_at is None) and completed==payload[:stop_at] and not received
    return len(completed)


def check():
    cases=dict(original_ff3_late_identity=run(0x7d,WORK,1),
               ff3=run(0x7d,OUT,1),kirby=run(0x7c,OUT,2),
               unready=run(0x7d,OUT,20),menu_timeout=run(0x7d,OUT,0,True),
               bytes_completed=write_page(),first_failed_ready=write_page(17))
    (OUT/'return.json').write_text(json.dumps(cases,indent=2))
    return cases

if __name__=='__main__':
    print(check())
