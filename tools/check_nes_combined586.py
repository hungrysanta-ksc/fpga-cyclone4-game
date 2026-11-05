# SPDX-License-Identifier: MIT
"""Actual linked586 receiver and transport tests; endpoint timing is modeled."""
import argparse,json,struct
from pathlib import Path
import check_nes_transport584 as old
from check_nes_transport584 import Probe as Base, result
from check_nes_game478 import encode,sha
from nes_abi582 import input_packets
from nes_row583 import encode_rows

ROOT=Path(__file__).resolve().parents[1]
def packets(geom,raw,g,serial=1,previous=None):
    _,counts,arrays=encode(geom,raw,g);allarrays=arrays+[list(raw)]
    blocks=encode_rows(allarrays,previous)
    c=input_packets(allarrays,[],serial,serial-1 if previous is not None else 0)
    begin=bytearray(c[0][:32]);begin[16:18]=g.to_bytes(2,'little')
    commit=bytearray(c[2]);commit[2:4]=g.to_bytes(2,'little')
    out=[];p=bytearray(begin);marks={}
    for rawpart in (False,True):
        for b in blocks:
            if (b[0]==6)!=rawpart:continue
            if len(p)+len(b)>254:out.append(bytes(p));p.clear()
            p+=b
        tail=c[1] if rawpart else c[0][32:]
        if len(p)+8>254:out.append(bytes(p));p.clear()
        marks['END' if rawpart else 'META_END']=(len(out),len(p))
        p+=tail;out.append(bytes(p));p.clear()
    out.append(bytes(commit))
    return out,counts,arrays,allarrays,blocks,marks

class Probe(Base):
    def __init__(self,*args,**kw):
        self.nonzero_dummy_calls=0
        super().__init__(*args,**kw)
    def output_exchange(self,tx):
        if tx[0] in (0xe1,0xe9):
            real=19+int.from_bytes(tx[13:15],'little') if tx[0]==0xe1 else 8+int.from_bytes(tx[1:3],'little')
            if any(tx[real:]):self.nonzero_dummy_calls+=1
            # New contract: declared payload/trailer only; remaining TX clocks
            # carry ignored bytes. The physical callback still sees original TX.
            tx=tx[:real]+bytes(len(tx)-real)
        return super().output_exchange(tx)
    def source(self,data,g):
        original=old.legacy_packets
        old.legacy_packets=lambda geom,raw,g:packets(geom,raw,g)[:3]
        try:return super().source(data,g)
        finally:old.legacy_packets=original

def equal(m,geom,raw):
    _,counts,_=encode(geom,raw,905);off=0
    for field,n,w,cap in zip(('maps','rows','objects','exceptions','raster','palette'),counts,(2,1,8,4,8,1),(1056,224,128,128,224,64)):
        assert bytes(m.u.mem_read(m.state+m.layout['nes_native165'][field],n*w))==geom[off:off+n*w],field
        off+=cap*w
    assert bytes(m.u.mem_read(m.state+m.layout['nes_native165']['raw_pixels'],len(raw)))==raw

def deliver(m,ps,token,prepare=True):
    for i,b in enumerate(ps):
        if i==len(ps)-1 and prepare and b[:2]==b'\x03\xf0':
            assert m.state_value()==2
            # Direct packet test's PREPARE grant only; transport tests execute
            # the actual prepare function and finite source endpoint separately.
            m.put(m.state,'nes_native165','state',3,1)
        m.u.mem_write(m.q,b)
        if not m.call('nes_native165_packet',[m.state,token,m.q,len(b)]):return False,token
        token=(token+1)&65535
    return True,token

def sequential(a):
    m=Probe(a.arm,True,128);prior=None;token=65520;rows=[]
    pins=json.loads((ROOT/'analysis/body581-verification.json').read_text())
    for g in range(905,958):
        gp=a.data/f'frame{g}.geometry';rp=a.data/f'frame{g}.raw'
        assert sha(gp)==pins['inputs'][gp.name] and sha(rp)==pins['inputs'][rp.name]
        geom=gp.read_bytes();raw=rp.read_bytes();ps,_,_,arrays,_,_=packets(geom,raw,g,g-904,prior)
        before=m.instructions;ok,token=deliver(m,ps,token);assert ok,(g,m.state_value(),m.get(m.state,'nes_native165','error',1))
        assert m.state_value()==4;equal(m,geom,raw)
        rows.append(dict(generation=g,packets=len(ps),payload_B=sum(map(len,ps)),instructions=m.instructions-before))
        m.call('nes_native165_consumed',[m.state]);prior=arrays
    return dict(frames=rows,**result(m))

def malformed(a):
    geom=(a.data/'frame905.geometry').read_bytes();raw=(a.data/'frame905.raw').read_bytes()
    cold=packets(geom,raw,905);rows=[]
    for fault in ('short_BEGIN','bad_version','bad_count','bad_epoch','bad_serial','base_without_history',
                  'block_zero_count','block_index','bad_map_value','META_CRC','END_CRC','early_COMMIT',
                  'token_repeat','oversize255','inherited_corruption'):
        m=Probe(a.arm,True,128);token=65520;ps=list(cold[0]);prepare=True
        if fault=='inherited_corruption':
            ok,token=deliver(m,ps,token);assert ok;m.call('nes_native165_consumed',[m.state])
            addr=m.state+m.layout['nes_native165']['maps'];b=bytearray(m.u.mem_read(addr,2));b[0]^=1;m.u.mem_write(addr,bytes(b))
            ps=packets(geom,raw,906,2,cold[3])[0]
        elif fault=='short_BEGIN':ps=[ps[0][:31]]
        elif fault=='early_COMMIT':prepare=False
        elif fault=='token_repeat':
            m.u.mem_write(m.q,ps[0]);assert m.call('nes_native165_packet',[m.state,token,m.q,len(ps[0])]);ps=[ps[0]]
        elif fault=='oversize255':ps=[bytes(255)]
        else:
            idx=0;b=bytearray(ps[0])
            if fault in ('META_CRC','END_CRC'):
                idx,at=cold[5]['META_END' if fault=='META_CRC' else 'END'];b=bytearray(ps[idx]);b[at+6]^=1
            elif fault=='bad_version':b[2]=2
            elif fault=='bad_count':b[18:20]=b'\x01\x00'
            elif fault=='bad_epoch':b[4:8]=bytes(4)
            elif fault=='bad_serial':b[8:12]=(2).to_bytes(4,'little')
            elif fault=='base_without_history':b[3]=1;b[12:16]=(1).to_bytes(4,'little')
            elif fault=='block_zero_count':b[36:38]=bytes(2)
            elif fault=='block_index':b[34:36]=(33).to_bytes(2,'little')
            elif fault=='bad_map_value':b[39]|=128
            ps[idx]=bytes(b)
        ok,_=deliver(m,ps,token,prepare);assert not ok,fault
        assert m.state_value()==5 and not m.get(m.state,'nes_native165','base_valid586',1),fault
        rows.append(dict(fault=fault,rejected=True,error=m.get(m.state,'nes_native165','error',1)))
    return rows

def suffix(a):
    rows=[]
    for cut in range(1,8):
        m=Probe(a.arm,True,128);g=951;m.ep.generation=g
        assert m.call('nes_resident211_begin',[m.resident,1,1,g,m.writer|1,0])
        assert m.call('nes_sink212_begin',[m.s,m.resident])
        plans=json.loads((a.plans/f'frame{g}/plans.json').read_text())
        q=bytearray(next(bytes.fromhex(h) for _,h in plans if bytes.fromhex(h)[6]==1))
        slots=list(range(cut))+list(range(32,32+15-cut))
        for slot in slots:
            q[2:4]=slot.to_bytes(2,'little');m.u.mem_write(m.q,bytes(q))
            assert m.call('nes_plan200_emit',[m.p,m.q])
        assert m.get(m.p,'nes_plan200','count',1)==15-cut
        at=m.p+m.layout['nes_plan200']['buffer']+4
        kept=bytes(m.u.mem_read(at,(15-cut)*8))
        assert [kept[i*8+3] for i in range(15-cut)]==slots[cut:]
        assert m.call('nes_plan200_end',[m.p]) and m.call('nes_plan200_progress',[m.p,1])
        assert [p[1] for p in m.ep.plans]==slots
        rows.append(dict(cut=cut,kept=15-cut,plans=15,nonzero_dummy_calls=m.nonzero_dummy_calls,passed=True))
    return rows

def arguments(a):
    m=Probe(a.arm,True,128);before=len(m.calls)
    assert not m.call('nes_native165_poll',[m.state,0,m.rt,m.ingress])
    saved=m.get(m.ingress,'nes_ingress584','buffer586',4)
    m.put(m.ingress,'nes_ingress584','buffer586',0,4)
    assert not m.call('nes_native165_poll',[m.state,m.fn,m.rt,m.ingress])
    m.put(m.ingress,'nes_ingress584','buffer586',saved,4)
    geom=(a.data/'frame905.geometry').read_bytes();raw=(a.data/'frame905.raw').read_bytes()
    ok,_=deliver(m,packets(geom,raw,905)[0][:-1],65520);assert ok and m.state_value()==2
    assert not m.call('nes_native165_prepare',[m.state,1,0,m.rt,m.ingress])
    assert len(m.calls)==before and m.state_value()==2
    return ['poll_NULL_callback','poll_NULL_RX_owner','prepare_NULL_callback']

def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    seq=sequential(a);(a.out/'sequential.json').write_text(json.dumps(seq,indent=2)+'\n')
    guards=malformed(a);pairs=[]
    for g in (951,954):
        for delay in (128,12000):
            m=Probe(a.arm,True,delay);assert m.source(a.data,g);source=result(m)
            assert m.output(a.plans,g),(g,delay,m.get(m.rt,'nes_native_runtime165','result',1),m.get(m.p,'nes_plan200','error',1))
            pairs.append(dict(generation=g,delay=delay,source=source,total=result(m)))
    faults=[]
    for fault in ('source_crc','source_epoch','source_token','STOP_after_header','STOP_after_body','early_COMMIT',
                  'snapshot_crc','snapshot_epoch','snapshot_generation','snapshot_sequence','future_credit',
                  'wrong_ACK','STOP_after_E9','STOP_after_E1','ambiguous_E1','no_final_ACK','driver_length255','driver_length256'):
        m=Probe(a.arm,True,12000,fault);ok=m.source(a.data,951)
        if ok:ok=m.output(a.plans,951)
        assert not ok,fault;faults.append(dict(fault=fault,rejected=True,**result(m)))
    m=Probe(a.arm,True,128);assert m.source(a.data,951);m.pressure(a.trace,951)
    report=dict(stage=586,passed=True,sequential=seq,parser_guards=guards,transport=pairs,transport_faults=faults,
        E9_suffix=suffix(a),argument_guards=arguments(a),pressure=result(m),firmware_B=(a.arm/'obj-nes-100/firmware.stm').stat().st_size,
        firmware_SHA256=sha(a.arm/'obj-nes-100/firmware.stm'),checker_SHA256=sha(Path(__file__)),
        scope=__doc__,history_implemented=False,R3_selected=False,
        limits=['Direct53 packet replay grants PREPARE in harness; separate951/954 execute source prepare',
          'Output uses7 real plans and modeled consume/final grant, not full65816/IRQ/ROM/VBlank',
          'No physical peripheral execution, actual two-slot RTL or new hardware FPS',
          'History shadow/stale/integrity and changed planner not implemented; cost gate already exceeded'])
    (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,frames=53,parser_faults=len(guards),transport_faults=len(faults),firmware_B=report['firmware_B'])))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','data','plans','trace','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
