"""Timestamp decoded prefixes, confirmed POPs and resident writes in the unmodified 604 binary."""
import argparse
import json
from pathlib import Path
import re
import struct

from check_nes_game478 import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1
from check_nes_rows604 import Runtime, check_geometry, fixture, simulate
from check_nes_wire600 import ROOT, pin, read


class Trace(Runtime):
    def input_exchange(self,tx):
        op=tx[0]
        if op==0xd2:
            off=self.layout['nes_native165']['at']
            self.prefix.append(dict(token=int.from_bytes(tx[2:4],'big'),accepted_ms=self.stamp()/1e6,
                                    at=list(struct.unpack('<6H',self.u.mem_read(self.state+off,12)))))
        rx=super().input_exchange(tx)
        if op==0xd0 and self.prefix and 'D0_end_ms' not in self.prefix[-1]:
            block=self.prefix[-1]
            assert int.from_bytes(rx[3:5],'big')==block['token']+1
            block['D0_end_ms']=self.stamp()/1e6
        return rx

    def hook(self,u,at,size,user):
        if hasattr(self,'prefix') and at==self.syms.get('nes_native165_poll'):
            self.poll_return=u.reg_read(UC_ARM_REG_LR)&~1
        if at==getattr(self,'poll_return',None):
            self.poll_return=None
            if self.prefix and 'confirmed_ms' not in self.prefix[-1]:
                assert u.reg_read(UC_ARM_REG_R0)==1 and 'D0_end_ms' in self.prefix[-1]
                self.prefix[-1]['confirmed_ms']=self.stamp()/1e6
        if hasattr(self,'prefix') and at==self.syms.get('nes_plan200_emit'):
            q=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),8))
            gen,slot,tag,kind,_=struct.unpack('<HHHBB',q)
            self.emits.append(dict(generation=gen,slot=slot,tag=tag,kind=kind,ms=self.stamp()/1e6))
        super().hook(u,at,size,user)


def map_records(blocks):
    result=[]
    for b,packet in enumerate(blocks):
        i=3
        while i<len(packet):
            tag=int.from_bytes(packet[i:i+2],'big')
            k,idx=divmod(tag,8192)
            width=8 if k==0 and idx&4096 else (2,1,7,4,7,1,2,8)[k]
            value=int.from_bytes(packet[i+2:i+2+width],'big')
            if k==0 and idx&4096:
                count=value>>60
                assert (idx&4095)==len(result) and 0<count<=4
                for j in range(count):
                    result.append((b,i,(value>>(15*(count-1-j)))&8191))
            elif tag&0xff00==0xd000:
                result.extend([(b,i,value&8191)]*((idx&255)+1))
            elif k==0:
                assert idx==len(result)
                result.append((b,i,value&8191))
            i+=width+2
        assert i==len(packet)
    return result


def capture(d,src,a,link,candidate):
    before=read(ROOT/'analysis/rows604-verification.json')['rows']
    pin(src/'obj-nes-100/firmware.stm',before['firmware_SHA256'])
    p=read(ROOT/'analysis/whole580-verification.json')['phases']
    assert p[0]['parameters']['driver_extra_us']==p[1]['parameters']['driver_extra_us']
    rows=[]
    for g in (952,954):
        geom,raw=fixture(a.data,d,g)
        m=Trace(src,False,400)
        lut=re.search(r'\{(.+?)\}',(src/'nes_palette165.inc').read_text())[1]
        m.u.mem_write(m.lut,struct.pack('<64H',*map(int,lut.split(','))))
        assert link.request('reset')=='OK'
        m.start(link,g,a.warm,p[0]['parameters']['driver_extra_us'],'normal')
        m.prefix=[];m.emits=[]
        for _ in range(512):
            assert m.call('nes_runtime165_step',[m.rt])
            if m.saw_ea:break
        assert m.saw_ea and m.saw_seal and m.state_value()==0
        check_geometry(m,geom,raw)
        prior=[r for r in before['frames'] if r['generation']==g]
        assert len(prior)==2 and all(r['first_BG']==m.first_bg for r in prior)
        words=map_records(m.blocks)
        count=struct.unpack_from('<H',geom,5728)[0]
        assert [w[2] for w in words]==[x&8191 for x in struct.unpack_from('<%dH'%count,geom)]
        for i,b in enumerate(m.prefix):
            assert sum(w[0]<=i for w in words)==b['at'][0]
        first=[e for e in m.emits if e['ms']<m.first_bg['end_ns']/1e6]
        assert len(first)==4 and first[0]['kind']==2 and all(e['kind']==0 for e in first[1:])
        for e in first[1:]:
            j=next(i for i,w in enumerate(words) if w[2]==e['tag'])
            b,off,_=words[j]
            e.update(map_index=j,D1_token=m.prefix[b]['token'],D1_record_offset=off,
                     tag_confirmed_ms=m.prefix[b]['confirmed_ms'])
        # Select before looking at the planner using only the accepted first map prefix.
        first_tags=list(dict.fromkeys(w[2] for w in words if w[0]==0))[:3]
        assert len(first_tags)==3
        rows.append(dict(generation=g,prefix=m.prefix,first_E9=m.first_bg,actual_first_plans=first,
                         first_three_distinct_tags=first_tags,final_ACK_and_EA=True))
        (d/f'capture-{g}.json').write_text(json.dumps(rows[-1],indent=2))
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('board','probe','arm','warm','data','out','report'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    result=simulate(a,'trace',a.arm/'src',True,capture)
    a.report.write_bytes((json.dumps(result,indent=2)+'\n').encode())
