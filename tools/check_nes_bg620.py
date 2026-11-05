# SPDX-License-Identifier: MIT
"""Exercise the linked second-plan edge, its error owner, and diagnostic buffers."""
import argparse
import hashlib
import json
from pathlib import Path
from check_nes_supply485_arm import ARM, sha
from check_nes_game478 import UC_HOOK_CODE
from check_nes_oam618_arm import check as oam_edge


def budget(src, sizes):
    m=ARM(src,'normal')
    m.u.mem_write(m.data_symbols['nes_startup222'],bytes(range(1,57)))
    ptr=0x20019800  # outside linked WRAM, below the fixture stack
    data=[]
    for size in sizes:
        m.u.mem_write(ptr,bytes([0xa5])*8193)
        n=m.call('nes_budget210_format',[ptr,size])
        assert m.u.mem_read(ptr+size,1)==b'\xa5'
        b=bytes(m.u.mem_read(ptr,n+1)) if n!=0xffffffff else b''
        assert not b or b.endswith(b'\0') and b'boot_schema=214' in b
        data.append((n,hashlib.sha256(b).hexdigest()))
    return data


def edge(src,count,mode,previous=1):
    m=ARM(src,'normal');m.setup()
    for field,value,size in [('early',1,1),('sent',previous,2),('defer_first',1,1)]:
        m.put(m.p,'nes_plan200',field,value,size)
    m.endpoint.accepted=previous
    exchange=m.endpoint.exchange
    def endpoint(tx,t):
        rx=exchange(tx,t)
        if tx[0]==0xe8:
            if mode=='STOP_before_E9':m.endpoint.mode='STOP_after_E9'
            if mode=='bad_reply':return rx[:-1]+bytes([rx[-1]^1])
        if tx[0]==0xe9 and mode=='STOP_after_E9':m.endpoint.mode='STOP_after_E9'
        return rx
    m.endpoint.exchange=endpoint
    for i in range(count-1):assert m.emit(0,100+i,1000+i) and m.endpoint.accepted==previous
    ok=m.emit(0,100+count-1,1000+count-1)
    sent=mode in ('normal','STOP_after_E9')
    assert bool(ok)==sent and m.endpoint.accepted==previous+int(sent)
    assert m.get(m.p,'nes_plan200','count')==(0 if sent else count)
    assert not m.get(m.s,'nes_native_sink165','displayed') and not m.endpoint.rearmed
    if sent:assert m.endpoint.plans==[(0,100+i,1000+i) for i in range(count)]
    if mode!='normal':
        before=len(m.endpoint.calls)
        assert not m.emit(0,255,1024) and len(m.endpoint.calls)==before
    return dict(mode=mode,issued=sent,previous_batches=previous,count=count,final_grant=False)


def drain_stop(src):
    m=ARM(src,'normal');m.setup()
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    m.put(m.s,'nes_native_sink165','map_next',64,1)
    for field,value,n in [('serial',1,4),('generation',907,2),('prepared',1,1),('open',1,1),('map_upload',0x7ffff<<32,8)]:
        m.put(m.resident,'nes_resident211',field,value,n)
    for field,value,n in [('valid',1,1),('generation',907,2),('bg_count',1,2),('hdma_size',3,2),('display_mask',30,1)]:
        m.put(m.video,'nes_native_video165',field,value,n)
    reached=[]
    def stop(u,at,size,user):
        reached.append(at)
        m.endpoint.mode='STOP_after_E9';m.endpoint.accepted=1
    pc=m.syms['nes_window184_drain'];m.u.hook_add(UC_HOOK_CODE,stop,begin=pc,end=pc)
    before=len(m.endpoint.calls)
    assert not m.call('nes_sink212_seal',[m.s,m.video,m.resident])
    assert reached==[pc] and len(m.endpoint.calls)==before and m.get(m.s,'nes_native_sink165','error')==5
    assert not m.get(m.s,'nes_native_sink165','displayed')
    return dict(STOP_at_map_drain=True,new_transactions=0,final_grant=False)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for opt in ('base','trial','out'):p.add_argument('--'+opt,type=Path,required=True)
    p.add_argument('--count',type=int,choices=(6,7),required=True)
    p.add_argument('--drain',action='store_true')
    a=p.parse_args()
    n=budget(a.base,[8192])[0][0];assert 0<n<8192
    sizes=[0,32,512,n,n+1,8192]
    reports=budget(a.trial,sizes)
    assert reports==budget(a.base,sizes)
    cases=[(1,a.count)]+([(2,1)] if a.count==6 else [])
    rows=[edge(a.trial,count,m,previous) for previous,count in cases
          for m in ('normal','bad_reply','STOP_before_E9','STOP_after_E9')]
    extra=dict(drain_STOP=drain_stop(a.trial),OAM=[oam_edge(a.trial,n,k) for n,k in ((18,0),(19,0),(19,1),(19,2))]) if a.drain else {}
    a.out.write_text(json.dumps(dict(arm=sha(a.trial/'obj-nes-100/firmware.stm'),budget=sizes,
                                     reports=reports,edges=rows,**extra),indent=2)+'\n')
