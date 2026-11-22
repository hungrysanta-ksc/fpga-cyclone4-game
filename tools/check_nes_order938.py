"""Check the linked marker dispatch through the 384 KiB SD probe call."""
import json
from check_nes_game478 import (Machine, ELFFile, UC_HOOK_CODE, UC_ARM_REG_LR,
                              UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1)
from nes_order938 import work, sha


def run(mode):
    arm=work(mode)
    src=arm/'link/src'
    m=Machine(src,bytes(128))
    m.u.mem_map(0xe000e000,0x1000)
    with (src/'obj-nes-100/sd2snes.elf').open('rb') as file:
        syms={s.name:s['st_value'] for s in ELFFile(file).get_section_by_name('.symtab').iter_symbols()}
    observed=[]
    def board(cpu,pc,size,name):
        if name=='printf':
            observed.append(cpu.reg_read(UC_ARM_REG_R1))
        cpu.reg_write(UC_ARM_REG_R0,int(name=='nes_menu_sd_probe'))
        cpu.reg_write(UC_ARM_REG_PC,cpu.reg_read(UC_ARM_REG_LR))
    for name in ('snes_reset','nes_cf86_failed094','nes_return_failed','nes_return_reset',
                 'nes_diag_sd_reset','nes_diag_begin','nes_budget210_reset','nes_cost471_reset_report',
                 'printf','nes_menu_sd_probe'):
        at=m.syms[name]
        m.u.hook_add(UC_HOOK_CODE,board,name,begin=at,end=at)
    rows={}
    for marker,boot,trace in [('MMC3',0,0),('START',1,0),('BOOT',2,0),
                              ('EARLY',0,1),('LATE',0,2),('CONTROL',0,3)]:
        m.u.mem_write(syms['pending'],bytes(1))
        m.u.mem_write(0x20012000,f'/sd2snes/NES {marker} 925.nh1\0'.encode())
        observed.clear()
        assert m.call('nes_menu_diagnostic_run',[0x20012000])==1
        assert observed==[384]
        assert m.u.mem_read(syms['nes_boot_probe798'],1)[0]==boot
        assert m.u.mem_read(syms['mode900'],1)[0]==trace
        assert not m.call('nes_menu_entry_only113',[]) and not m.call('nes_menu_base_only116',[])
        rows[marker]=dict(geometry=observed[0],boot=boot,trace=trace)
    result=dict(firmware=sha(src/'obj-nes-100/firmware.stm'),modes=rows)
    (arm/'dispatch938.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    import sys
    print(run(sys.argv[1]))
