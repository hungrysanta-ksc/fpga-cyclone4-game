"""Feed the 78 physical summary rows to the release ARM and check its saved detail."""
import sys
from pathlib import Path
from check_nes_frame862_arm import TimedProbe, UC_HOOK_CODE, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
from read_nes_supply905 import CAP, ROW, TRACE_BYTES, decode
from prepare_nes_trial907 import WORK
from package_nes_trial704 import save,sha
from check_nes_longrun693 import ELFFile, member_offset


def verify(trace,work=WORK,edition=907):
    baseline=decode(trace,905 if edition==907 else 907)
    selected=baseline['selected']-1
    assert not any(baseline['dropped']) and baseline['rows'][selected]['generation']==(1079 if edition==907 else 1212)
    raw=trace.read_bytes()
    entries=raw[16+CAP*ROW.size+4:]
    src=work/'link/src'
    m=TimedProbe(src)
    with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
        elf=ELFFile(f)
        step=edition==915 and bool(elf.get_section_by_name('.symtab').get_symbol_by_name('step_begin915'))
        if edition==915:
            commit_vars={name:elf.get_section_by_name('.symtab').get_symbol_by_name(name)[0]['st_value']
                         for name in (('commit_clock915','commit_gen915','step_begin915') if step else ('commit_clock915','commit_gen915'))}
        layout=next(d for cu in elf.get_dwarf_info().iter_CUs() for d in cu.iter_DIEs()
                    if d.tag=='DW_TAG_structure_type' and 'DW_AT_byte_size' in d.attributes
                    and 'DW_AT_name' in d.attributes and d.attributes['DW_AT_name'].value==b'nes_plan200')
        m.layout['nes_plan200']={c.attributes['DW_AT_name'].value.decode():member_offset(c)
                                 for c in layout.iter_children() if c.tag=='DW_TAG_member'}
    m.u.mem_write(m.data['mode900'],b'\0')
    m.call('nes_budget210_reset',[])
    plan=m.rt+m.layout['nes_native_runtime165']['plan']
    def spi(cpu,*_):
        tx=cpu.reg_read(UC_ARM_REG_R1)
        assert cpu.reg_read(UC_ARM_REG_R3)==32 and 0x20000000<=tx<0x20010000
        cmd,page=cpu.mem_read(tx,2)
        assert cmd==0x78
        offset=page*16
        # Only the baseline-selected row has physical detail pages.
        body=entries[offset:offset+16] if index==selected else bytes(16)
        if edition==915:
            m.u.mem_write(0xe0001004,(100000000+24*512).to_bytes(4,'little'))
        cpu.mem_write(cpu.reg_read(UC_ARM_REG_R2),header+body)
        m.ret(cpu,1)
    address=m.syms['nes_native165_bulk']
    m.u.hook_add(UC_HOOK_CODE,spi,begin=address,end=address)
    for index,r in enumerate(baseline['rows']):
        tick,g,bg,ia,ea,_,obj,dirty,flags,bank,header,desc=ROW.unpack_from(raw,16+index*ROW.size)
        assert flags==7
        for name,value,width in [('generation',g,2),('bg_count',bg,2),('obj_count',obj,2),('map_dirty',(1<<dirty)-1,8)]:
            m.put(m.video,'nes_native_video165',name,value,width)
        m.put(plan,'nes_plan200','bulk_valid',int(bool(r['chunks'])),1)
        m.u.mem_write(plan+m.layout['nes_plan200']['bulk'],desc)
        # Changing only target latency must not make the faster workload lose
        # the sole detail slot to a slower but unrelated screen.
        if index==selected:ia=ea+64
        if edition==915:
            m.u.mem_write(commit_vars['commit_gen915'],g.to_bytes(2,'little'))
            m.u.mem_write(commit_vars['commit_clock915'],(100000000-(ea+32)*512).to_bytes(4,'little'))
            if step:m.u.mem_write(commit_vars['step_begin915'],(100000000-(ea+48)*512).to_bytes(4,'little'))
        for name,age,args in [('input900',ia,[g]),('e0900',ea,[g,bank])]:
            m.u.mem_write(0xe0001004,(100000000-age*512).to_bytes(4,'little'))
            m.call(name,args)
        m.u.mem_write(0xe0001004,(100000000).to_bytes(4,'little'))
        m.call('nes_budget210_frame',[tick])
        m.call('nes_budget210_display',[tick,m.video])
    dest=work/'proof/selector.bin'
    dest.write_bytes(m.u.mem_read(m.data['ptrcache'],TRACE_BYTES[edition]+2*step))
    d=decode(dest,edition,direct_probe=edition==915 and not step)
    row=d['rows'][selected]
    assert d['selected']==selected+1 and row['detail']==baseline['rows'][selected]['detail']
    assert row['input_to_final_ACK_ms']==0.390 and d['displayed55']==len(baseline['rows'])
    if edition==915:
        assert row['commit_age_ticks512']==row['ACK_age_ticks512']+32 and row['first_query_ticks512']==24
        if step:assert row['commit_step_ticks512']==16
    save(work/'proof/selector.json',dict(firmware=sha(src/'obj-nes-100/firmware.stm'),baseline=sha(trace),
         rows=len(d['rows']),selected_generation=row['generation'],retained_grants=sum(c['ROM_grants'] for c in row['detail']),
         injected_input_to_ACK_ms=row['input_to_final_ACK_ms']))


if __name__=='__main__':verify(Path(sys.argv[1]))
