# SPDX-License-Identifier: MIT
"""Execute the linked menu preparation/release gates with modeled log, IRQ and checkpoint I/O."""
import argparse
import json
from pathlib import Path
from check_nes_game478 import Machine,ELFFile,UC_HOOK_CODE,UC_ARM_REG_R0,UC_ARM_REG_LR,UC_ARM_REG_PC,sha


def check(src,trial='533'):
    m=Machine(src,bytes(128))
    with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
        data={s.name:s['st_value'] for s in ELFFile(f).get_section_by_name('.symtab').iter_symbols()
              if s.name in ('pending','safe_to_reload','prepared','saved_irq')}
    def string_at(at):
        return bytes(m.u.mem_read(at,64)).split(b'\0')[0].decode()
    calls=[]
    def io(cpu,pc,size,name):
        value=cpu.reg_read(UC_ARM_REG_R0)
        calls.append((name,string_at(value) if name in ('save_report','nes_checkpoint112') else None))
        answer=(name=='nes_return_failed' and mode=='latched') or (name=='nes_checkpoint112' and mode!='checkpoint')
        cpu.reg_write(UC_ARM_REG_R0,int(answer))
        cpu.reg_write(UC_ARM_REG_PC,cpu.reg_read(UC_ARM_REG_LR))
    for name in ('nes_return_failed','nes_return_log_allow','save_report','nes_checkpoint112','nes_diag_leave'):
        m.u.hook_add(UC_HOOK_CODE,io,name,begin=m.syms[name],end=m.syms[name])
    rows={}
    for mode in ('normal','base','menu','latched','checkpoint'):
        calls.clear()
        for n,v in [('pending',1),('prepared',0),('safe_to_reload',mode!='base'),('saved_irq',0)]:
            m.u.mem_write(data[n],bytes([v]))
        ok=m.call('nes_menu_diagnostic_prepared',[int(mode!='menu')])
        assert ok==(mode=='normal') and m.u.mem_read(data['prepared'],1)==bytes([ok])
        m.call('nes_menu_diagnostic_released',[])
        assert int(m.u.mem_read(data['pending'],1)[0])==1-ok
        assert calls.count(('nes_diag_leave',None))==ok
        assert calls.count(('save_report','RETURN_READY_RESET_RELEASED'))==ok
        assert calls.count(('nes_checkpoint112','MENU_PREPARED'))==(mode in ('normal','checkpoint'))
        rows[mode]=dict(prepared=ok,released=ok,calls=list(calls))
    for fname,valid in [(f'NES MMC3 {trial}.nh1',1),(f'/folder/NES MMC3 {trial}.nh1',1),('NES MMC3 529.nh1',0),(f'NES MMC3 {trial}.nes',0)]:
        addr=0x20012000
        m.u.mem_write(addr,fname.encode()+b'\0')
        assert m.call('nes_menu_diagnostic_marker',[addr])==valid
    return dict(firmware=sha(src/'obj-nes-100/firmware.stm'),rows=rows,marker_cases=4)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--arm',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--trial',default='533')
    a=p.parse_args()
    a.out.write_text(json.dumps(check(a.arm,a.trial),indent=2)+'\n')
