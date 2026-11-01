# SPDX-License-Identifier: MIT
"""Linked frozen-map offer with credit, bulk ownership, identity and STOP faults."""
import argparse,json
from pathlib import Path
from check_nes_tile532 import ARM,Window,ELFFile,member_offset
from nes_raw506 import sha


def check(src,mode,after_tile=False):
    m=ARM(src,mode);ep=Window(mode);m.endpoint=ep
    with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
        d=next(d for cu in ELFFile(f).get_dwarf_info().iter_CUs() for d in cu.iter_DIEs()
               if d.tag=='DW_TAG_structure_type' and d.attributes.get('DW_AT_name') and
               d.attributes['DW_AT_name'].value==b'nes_native_runtime165' and 'DW_AT_byte_size' in d.attributes)
        fields={c.attributes['DW_AT_name'].value.decode():member_offset(c) for c in d.iter_children() if c.tag=='DW_TAG_member'}
    rt=m.p;m.p,m.w,m.s=[rt+fields[k] for k in ('plan','transport','sink')];m.setup()
    for k,v in [('video',m.video),('resident',m.resident)]:m.u.mem_write(rt+fields[k],v.to_bytes(4,'little'))
    for k,v,n in [('ctx',rt,4),('generation',907,2),('started',1,1),('bulk_pending',1,1),('bulk_until',65532,2)]:m.put(m.p,'nes_plan200',k,v,n)
    ep.sent=65532;ep.retired=65529;ep.live=True
    head=bytes([7,0,0,0,1,0,0,0,139,3]);ep.last=bytes([0,7])+head[2:10]+b'\x65\x9a'
    for k,v,n in [('sent',ep.sent,2),('retired',ep.retired,2),('ever_sent',1,1)]:m.put(m.w,'nes_sink_window184',k,v,n)
    m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],head)
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    for k,v,n in [('open',1,1),('generation',907,2),('target',0,1),('map_stale',0x5555,8)]:m.put(m.resident,'nes_resident211',k,v,n)
    m.put(m.video,'nes_native_video165','generation',907,2)
    before=len(ep.calls)
    if mode in ('closed','fault','stale_resident','stale_video'):
        if mode=='closed':m.put(m.resident,'nes_resident211','open',0,1)
        if mode=='fault':m.put(m.resident,'nes_resident211','fault',1,1)
        if mode=='stale_resident':m.put(m.resident,'nes_resident211','generation',906,2)
        if mode=='stale_video':m.put(m.video,'nes_native_video165','generation',906,2)
        assert m.call('quiet528',[rt])==0 and len(ep.calls)==before
        return dict(mode=mode,rejected_before_SPI=True)
    if mode=='bulk_target_edge':m.put(m.p,'nes_plan200','bulk_until',65529,2)
    if mode=='ready_tile' or mode.startswith('new_tile'):
        original=ep.exchange
        def exchange(tx,clock):
            if tx[0]==0xe8:
                # Same live bulk descriptor: polling must not offer a map or submit it twice.
                from check_nes_supply485_arm import crc
                ep.calls.append(tx.hex());b=bytearray(20);b[1:4]=bytes([0xd7,4,1])
                b[6:18]=bytes([1,0,16,0,0,0,139,3,1,0,0,0])
                if mode=='new_tile_wrong_gen':b[12]^=1
                b[19]=crc(b[1:19],8,7,0);return bytes(b)
            if tx[0]==0xe1 and tx[1]==7:
                from check_nes_supply485_arm import crc
                assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
                ep.calls.append(tx.hex());b=tx[1:-2]
                ep.sent=(ep.sent+1)&65535;ep.last=bytes([0,7])+b[2:10]+b'\x65\x9a'
                if mode=='new_tile_stop':ep.mode='STOP_after_bulk';ep.bulk=True
                return bytes(len(tx))
            return original(tx,clock)
        ep.exchange=exchange
        m.put(m.p,'nes_plan200','bulk_valid',int(mode=='ready_tile'),1)
        m.put(m.p,'nes_plan200','bulk_pending',int(mode=='ready_tile'),1)
        m.u.mem_write(m.p+m.layout['nes_plan200']['bulk'],bytes([1,0,16,0,0,0,139,3,1,0,0,0]))
        if mode=='new_tile_full':
            ep.retired=65530;m.put(m.w,'nes_sink_window184','retired',65530,2)
    ok=bool(m.call('offer527',[rt,1]))
    assert ok==(mode in ('normal','busy','bulk_target_edge','ready_tile','new_tile','new_tile_full')),(mode,ok)
    assert ep.writes==([0] if mode in ('normal','ambiguous_E1') or (mode=='new_tile' and after_tile) else []),(mode,ep.writes)
    if mode.startswith('new_tile'):
        assert [bytes.fromhex(x)[1] for x in ep.calls if x.startswith('e1')]==([] if mode=='new_tile_wrong_gen' else [7,4] if mode=='new_tile' and after_tile else [7])
    if mode=='normal':
        assert m.call('nes_plan200_end',[m.p])==1 and ep.end
        assert ep.writes==list(range(0,1024,128)) and ep.sent==4
        assert not m.get(m.p,'nes_plan200','bulk_pending')
    elif not ok:
        calls=len(ep.calls);assert m.call('offer527',[rt,1])==0 and len(ep.calls)==calls,mode
        assert not ep.end
    return dict(mode=mode,offer=ok,maps=len(ep.writes),END=ep.end,
                window_error=m.get(m.w,'nes_sink_window184','error'),SPI_count=len(ep.calls)-before)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--after-tile',action='store_true')
    a=p.parse_args()
    cases=['normal','busy','bulk_target_edge','ready_tile','new_tile','new_tile_full','bad_crc','bad_identity','STOP_after_refresh','ambiguous_E1','closed','fault','stale_resident','stale_video']
    if a.after_tile:cases+=['new_tile_stop','new_tile_wrong_gen']
    rows=[check(a.arm,n,a.after_tile) for n in cases]
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),rows=rows),indent=2)+'\n',encoding='utf8',newline='\n')
