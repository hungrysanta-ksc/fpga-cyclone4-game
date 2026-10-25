# SPDX-License-Identifier: MIT
"""Actual M4 bounded preparation, priority and cancellation; controlled GPIO."""
import argparse,binascii,json,struct
from pathlib import Path
from probe_nes_native289 import Producer
from probe_nes_decode280 import records,chunks
from guard_nes_irq284 import Endpoint
from nes_delta231 import BASE,sha

def setup(elf):
    ep=Endpoint();arm=Producer(elf,ep);ep.arm=arm
    for n in ('irq_init284','reset259','reset285','reset280'):arm.call(n,[])
    arm.uc.mem_write(arm.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes())
    for b in chunks(records(BASE/'probes/nes-joint284/test04/frame905.records')):
        arm.uc.mem_write(0x20028000,b);assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])
    for n in ('expand286','begin285','geometry_plan286','h2early286','input_commit286','begin_step286','begin_native290'):assert arm.call(n,[])
    for _ in range(2048):
        if arm.call('next_step286',[])==2:break
    else:raise AssertionError('planner did not complete')
    return arm

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    ref=setup(a.reference/'output.elf');assert ref.call('prepare289',[])
    expected=bytes(ref.uc.mem_read(ref.symbols['seal289'],206))
    arm=setup(a.source/'output.elf');snapshot=bytes(arm.uc.mem_read(0x20000000,0x40000));context=arm.uc.context_save()
    def word(n):return int.from_bytes(arm.uc.mem_read(arm.symbols[n],4),'little')
    def put(n,v):arm.uc.mem_write(arm.symbols[n],struct.pack('<I',v))
    def restore():arm.uc.mem_write(0x20000000,snapshot);arm.uc.context_restore(context);arm.gpio(0)
    rows=[];sizes=[]
    for i in range(12):
        before=arm.instructions;assert arm.call('prepare_slice309',[]);sizes.append(arm.instructions-before)
    assert word('prepared309')==207 and bytes(arm.uc.mem_read(arm.symbols['seal289'],206))==expected
    rows.append(dict(case='12 slices exactly match original seal',instructions=sizes))
    for label,cache,flags,phase,level,sent,retired,at,allowed in [
        ('blocked DMA wait',1,0,0,0,4,0,0,True),('DMA ready',1,0,2,0,4,0,0,False),
        ('plan writable',1,1,0,0,4,0,0,False),('plan unknown',0,0,0,0,4,0,0,False),
        ('IRQ high',1,0,0,1,4,0,0,False),('queue credit available',1,0,0,0,3,0,0,False),
        ('wrap full',1,0,0,0,1,65533,0,True)]:
        restore();arm.gpio(level)
        for n,v in dict(plan_at267=at,plan_bytes267=word('output_size285'),plan_cache282=cache,plan_flags282=flags,phase_ready302=phase,wait_reason302=8).items():put(n,v)
        arm.uc.mem_write(arm.symbols['state259'],struct.pack('<HH',sent,retired));before=arm.instructions
        assert arm.call('work302',[])==1
        assert (word('prepared309')==207)==allowed,(label,word('prepared309'))
        rows.append(dict(case=label,prepared=word('prepared309'),instructions=arm.instructions-before))
    for count in range(13):
        restore()
        for _ in range(count):assert arm.call('prepare_slice309',[])
        arm.call('stop286',[]);before=bytes(arm.uc.mem_read(arm.symbols['seal289'],206))
        assert not arm.call('prepare_slice309',[]) and not arm.call('prepare289',[])
        assert before==bytes(arm.uc.mem_read(arm.symbols['seal289'],206)) and not arm.call('commit285',[])
        rows.append(dict(case='STOP rejects preparation and commit',after_slices=count))
    # A GPIO edge between slices must prevent the next slice in work302.
    restore();assert arm.call('prepare_slice309',[]);arm.gpio(1)
    for n,v in dict(plan_at267=0,plan_bytes267=word('output_size285'),plan_cache282=1,plan_flags282=0,phase_ready302=0,wait_reason302=8).items():put(n,v)
    arm.uc.mem_write(arm.symbols['state259'],struct.pack('<HH',4,0));assert arm.call('work302',[])==1 and word('prepared309')==1
    rows.append(dict(case='IRQ between slices retains partial cursor',prepared=1))
    # ARM ABI: 3 pointers + serial32 + five uint16 fields precede state.
    restore();state=arm.symbols['sink289']+26;assert bytes(arm.uc.mem_read(state,1))==b'\x01'
    arm.uc.mem_write(state,b'\x02');arm.uc.mem_write(arm.symbols['wire259'],b'\xa5'*259)
    for _ in range(12):assert arm.call('prepare_slice309',[])
    assert bytes(arm.uc.mem_read(arm.symbols['seal289'],206))==expected
    assert bytes(arm.uc.mem_read(arm.symbols['wire259'],259))==b'\xa5'*259
    assert bytes(arm.uc.mem_read(state,1))==b'\x02' and not arm.call('prepare289',[])
    arm.uc.mem_write(state,b'\x01');assert arm.call('prepare289',[])
    rows.append(dict(case='BUSY private seal only; public prepare still requires BUILD'))
    arm.uc.mem_write(state,b'\x03');assert not arm.call('prepare_slice309',[])
    rows.append(dict(case='FAULT rejects completed cache'))
    r=dict(passed=True,checks=rows,max_slice_instructions=max(sizes),ELF_sha256=sha(a.source/'output.elf'),reference_ELF=sha(a.reference/'output.elf'),script_sha256=sha(Path(__file__)),scope='Actual M4 instructions; controlled credit/GPIO; intercepted sink; not live IRQ timing')
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps(r))
if __name__=='__main__':main()
