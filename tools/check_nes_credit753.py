# SPDX-License-Identifier: MIT
"""Check the actual input borrowed between two final ACK polls on the linked ARM."""
import argparse
import json
import struct
from pathlib import Path

from check_nes_receive682 import Burst, burst, crc
from check_nes_credit752 import verify


def check(src, policy, case):
    m = Burst(src, 'cap7')
    m.packets.extend(struct.pack('>HHH', i, 953, i) for i in (7,8))
    if policy=='large' and case!='small':
        # 22 packed 6-byte map records exceed the half-page threshold.
        m.packets[7]=b''.join(struct.pack('>HHH',i,953,i) for i in range(6,28))
        m.packets[8]=b''.join(struct.pack('>HHH',i,953,i) for i in range(28,50))
    if case=='wrap':
        m.start_token=65528
    # Start the real seven-block batch, arming any single-block allowance on
    # the COMMITTED -> next receiver transition. The returned D0 is cached.
    m.u.mem_write(0x20018000,bytes([0xa5])*0x8000)
    assert m.call('wait634',[m.rt,m.check|1,3,0]) and m.index==7
    assert m.get(m.state,'nes_native165','ready183') and m.state_value()==1
    if case=='wrong_kind':
        m.put(m.state,'nes_native165','next_kind',1,1)
    if case=='empty':
        m.put(m.state,'nes_native165','ready183',0,1)
    if case=='bad_token':
        ptr=m.state+m.layout['nes_native165']['status183']
        b=bytearray(m.u.mem_read(ptr,8));b[4]^=1;b[7]=crc(b[1:7],8,7,0);m.u.mem_write(ptr,bytes(b))
    if case in ('STOP_before','STOP_after_READ','bad_retire','bad_CRC','failed_IO'):
        m.case=case
    m.ops.clear()
    ok=m.call('wait634',[m.rt,m.check|1,2,int(case=='output_progress')])
    skipped=case in ('empty','output_progress','wrong_kind','small')
    good=case in ('normal','wrap') or skipped
    assert bool(ok)==good,(policy,case,ok,m.ops)
    if skipped:
        assert not m.ops and m.index==7
    elif good:
        assert m.ops==[0xd1,0xd2,0xd0] and m.index==8
        assert m.get(m.state,'nes_native165','next_token',2)==(0 if case=='wrap' else 8)
    else:
        assert m.index==(8 if case=='bad_retire' else 7)
    assert m.state_value()!=4 and not {0xd3,0xe0,0xe1,0xea}.intersection(m.ops)
    ops=list(m.ops)
    if good and not skipped:
        m.ops.clear()
        assert m.call('wait634',[m.rt,m.check|1,2,0])
        assert m.index==(8 if policy=='one' else 9)
    return dict(case=case,accepted=bool(ok),transactions=ops)


def obj_budget(src,kind,size,valid,history,prefix=False):
    from check_nes_game478 import ELFFile
    from test_nes_raw506_joint import member_offset
    m=Burst(src,'cap7')
    with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
        entries=(d for cu in ELFFile(f).get_dwarf_info().iter_CUs() for d in cu.iter_DIEs())
        plan=next(d for d in entries if d.tag=='DW_TAG_structure_type' and
                  d.attributes.get('DW_AT_name') and d.attributes['DW_AT_name'].value==b'nes_plan200'
                  and 'DW_AT_byte_size' in d.attributes)
        fields={c.attributes['DW_AT_name'].value.decode():member_offset(c)
                for c in plan.iter_children() if c.tag=='DW_TAG_member'}
    if prefix:
        # Six-byte literal records straddle the half-page threshold.
        records=size//6
        m.packets[7]=b''.join(struct.pack('>HHH',i,953,i) for i in range(6,6+records))
    base=m.rt+m.layout['nes_native_runtime165']['plan']
    for key,value in [('bank_history',history),('bulk_valid',valid)]:
        m.u.mem_write(base+fields[key],bytes([value]))
    m.u.mem_write(base+fields['bulk'],bytes([1,kind])+size.to_bytes(2,'little'))
    m.u.mem_write(0x20018000,bytes([0xa5])*0x8000)
    assert m.call('wait634',[m.rt,m.check|1,3,0])
    expected=8 if kind==1 and valid and history==2 and size>=128 else 7
    if prefix:expected=8 if len(m.packets[7])>=128 and history==2 else 7
    assert m.index==expected and not {0xd3,0xe1,0xea}.intersection(m.ops)
    return dict(kind=kind,size=size,valid=valid,history=history,reads=m.index)


def cached_status(src):
    # Keep all six checked data bytes and the CRC in scope, including the
    # valid cached case that does not issue a new D0 before READ.
    m=Burst(src,'cap7')
    m.u.mem_write(0x20018000,bytes([0xa5])*0x8000)
    assert m.call('wait634',[m.rt,m.check|1,3,0]) and m.index==7
    ptr=m.state+m.layout['nes_native165']['status183']
    valid=bytes(m.u.mem_read(ptr,8))
    for bit in range(56):
        bad=bytearray(valid)
        bad[1+bit//8]^=1<<(bit%8)
        m.u.mem_write(ptr,bytes(bad))
        m.put(m.state,'nes_native165','ready183',1,1)
        m.put(m.state,'nes_native165','state',1,1)
        m.ops.clear()
        assert not m.call('nes_native165_poll',[m.state,m.spi|1,0])
        assert not m.ops and m.index==7
    return 56


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('arm','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--policy',required=True)
    p.add_argument('--trial',default='690')
    a=p.parse_args()
    v=verify(a.arm,'mapobj',a.trial)
    cases=['normal','wrap','empty','output_progress','bad_token','STOP_before','STOP_after_READ','bad_CRC','bad_retire','failed_IO']
    if a.policy=='large':cases+=['small']
    if a.policy=='geometry':cases+=['wrong_kind']
    v['extra_input']=[] if (a.policy.endswith('crc') or a.policy in ('objburst','prefix')) else [check(a.arm,a.policy,c) for c in cases]
    if a.policy=='objburst':
        cases=[(1,128,1,2),(1,256,1,2),(1,96,1,2),(0,256,1,2),(1,256,0,2),(1,128,1,1)]
        v['obj_budget']=[obj_budget(a.arm,*c) for c in cases]
    if a.policy.startswith('prefix'):
        v['prefix_budget']=[obj_budget(a.arm,1,size,1,hist,True) for size,hist in [(132,2),(126,2),(132,1),(132,0)]]
    v['bad_cached_status_bits']=cached_status(a.arm) if a.policy=='inputcrc' else None
    v['initial_batch']=[burst(a.arm,c) for c in ('cap7','empty_after3','STOP_after3','CRC_third','cache_CRC','cache_token')]
    a.out.write_text(json.dumps(v,indent=2)+'\n',encoding='utf8',newline='\n')
