"""Exercise the linked page selector and reset, using member offsets from its own ELF."""
import struct
from elftools.elf.elffile import ELFFile
from elftools.dwarf.dwarf_expr import DWARFExprParser
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_MCLASS, UC_MODE_THUMB
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP
from nes_arm964 import ARM


def layout(elf):
    dwarf=elf.get_dwarf_info()
    parser=DWARFExprParser(dwarf.structs)
    for unit in dwarf.iter_CUs():
        for die in unit.iter_DIEs():
            if (die.tag!='DW_TAG_structure_type' or 'DW_AT_byte_size' not in die.attributes
                    or getattr(die.attributes.get('DW_AT_name'),'value',None)!=b'nes_native165'):
                continue
            fields={}
            for child in die.iter_children():
                name=getattr(child.attributes.get('DW_AT_name'),'value',None)
                if name in (b'objects',b'counts',b'obj_page_plus_one964'):
                    expr,=parser.parse_expr(child.attributes['DW_AT_data_member_location'].value)
                    assert expr.op_name=='DW_OP_plus_uconst'
                    fields[name.decode()]=expr.args[0]
            return fields
    raise ValueError('missing receiver structure')


def check():
    obj=ARM/'link/src/obj-nes-100'
    with (obj/'sd2snes.elf').open('rb') as f:
        elf=ELFFile(f)
        fields=layout(elf)
        symbols=elf.get_section_by_name('.symtab')
        entry={s:symbols.get_symbol_by_name(s)[0]['st_value'] for s in ('page964','nes_native165_reset')}
    cpu=Uc(UC_ARCH_ARM, UC_MODE_MCLASS|UC_MODE_THUMB)
    cpu.mem_map(0x08000000,0x80000)
    cpu.mem_map(0x20000000,0x20000)
    cpu.mem_write(0x0800c000,(obj/'firmware.stm').read_bytes())
    state,stop=0x20001000,0x20000100
    def call(name,base):
        cpu.reg_write(UC_ARM_REG_R0,state)
        cpu.reg_write(UC_ARM_REG_R1,base)
        cpu.reg_write(UC_ARM_REG_LR,stop|1)
        cpu.reg_write(UC_ARM_REG_SP,0x2001fff0)
        cpu.emu_start(entry[name]|1,stop,count=100000)
        assert cpu.reg_read(UC_ARM_REG_PC)==stop
    out=state+fields['obj_page_plus_one964']
    full=lambda base:[(base+i,255) for i in range(8)]
    cases=[(0,full(0),1),(8184,full(8184),8185),(16,full(19),0),
           (8,full(8)[:-1]+[(15,127)],0),(8,full(8)[:-1]+[(8,255)],0),(0,[],0)]
    for base,records,expected in cases:
        call('nes_native165_reset',0)
        assert cpu.mem_read(out,2)==bytes(2)
        cpu.mem_write(state+fields['counts']+4,struct.pack('<H',len(records)))
        for i,(tag,mask) in enumerate(records):
            cpu.mem_write(state+fields['objects']+i*8,struct.pack('<Q',tag|(mask<<38)))
        call('page964',base)
        assert int.from_bytes(cpu.mem_read(out,2),'little')==expected
    return len(cases)
