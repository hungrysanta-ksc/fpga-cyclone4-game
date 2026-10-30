# SPDX-License-Identifier: MIT
"""Actual linked489 ARM serializer, canonical tables and expired-scratch audit."""
import argparse
from collections import Counter
import hashlib,json,re,struct
from pathlib import Path
from audit_nes_output487 import Audit
from check_nes_game478 import Machine,encode,sha
def unpack_wire6(data,count):
    assert len(data)==192*count and 1<=count<=2
    raw=bytearray(2048);at=0
    for plane in range(3):
        for row in range(count):
            for tile in range(32):raw[tile*64+plane*16+row*2:tile*64+plane*16+row*2+2]=data[at:at+2];at+=2
    for tile in range(32):
        for row in range(count):raw[tile*64+48+row*2]=255
    return bytes(raw)

class CompactAudit(Audit):
    def call(self,name,args):
        if name!='nes_resident211_commit':return Machine.call(self,name,args)
        r=self.layout['nes_resident211'];v=self.layout['nes_native_video165'];s=self.layout['nes_native_sink165']
        read=lambda base,layout,key,n:int.from_bytes(self.u.mem_read(base+layout[key],n),'little')
        snapshot=bytes(self.u.mem_read(self.video,v['size']))
        self.bank=args[3];self.packets=[];self.function_counts.clear()
        self.u.mem_write(self.sink,bytes(s['size']))
        for key,value,n in [('exchange',self.exchange|1,4),('serial',args[1],4),('generation',args[2],2),('state',1,1),('displayed',read(self.resident,r,'displayed',1),1)]:self.u.mem_write(self.sink+s[key],value.to_bytes(n,'little'))
        self.collect=True
        try:ok=Machine.call(self,'nes_sink212_seal',[self.sink,self.video,self.resident])
        finally:self.collect=False
        assert ok==1
        descriptor=self.packets[-1][16:];lengths=struct.unpack_from('<6H',descriptor);count=int.from_bytes(descriptor[22:24],'little')
        assert descriptor[20:22]==b'\x91\x48'
        d=self.out/f'frame{args[2]}';d.mkdir()
        for k,key in [(2,'map'),(3,'cgram'),(4,'oam')]:
            expected=snapshot[v[key]:v[key]+lengths[k]]
            assert bytes(self.images[self.bank][k][:lengths[k]])==expected
            (d/f'expected-{key}.bin').write_bytes(expected)
        hdmasize=int.from_bytes(snapshot[v['hdma_size']:v['hdma_size']+2],'little')
        expected=snapshot[v['hdma']:v['hdma']+hdmasize]
        if count:
            expected+=bytes(1121-hdmasize)+snapshot[v['patch']:v['patch']+2291]+snapshot[v['patch']+2292:v['patch']+2298]
            wire=bytes(self.images[self.bank][5][:lengths[5]]);n=192*count
            if lengths[5]==3418:canonical=wire
            else:
                assert lengths[5]==1370+n
                canonical=wire[:1121]+unpack_wire6(wire[1121:1121+n],count)+wire[1121+n:]
        else:canonical=bytes(self.images[self.bank][5][:lengths[5]])
        assert canonical==expected
        (d/'expected-hdma.bin').write_bytes(expected)
        (d/'video-before.bin').write_bytes(snapshot)
        after=bytes(self.u.mem_read(self.video,v['size']))
        extent=192*count if count and count<=2 else 0
        assert after[:4096]==snapshot[:4096] and after[4096+extent:]==snapshot[4096+extent:],'write outside expired BG workspace'
        for i,p in enumerate(self.packets):(d/f'packet{i:03}.bin').write_bytes(p)
        canonical_state=bytes(self.u.mem_read(self.state,self.layout['nes_native165']['size']))+snapshot+bytes(self.u.mem_read(self.resident,r['size']))
        self.canonical_state_SHA256=hashlib.sha256(canonical_state).hexdigest()
        sections=Counter();packets=Counter()
        for p in self.packets:
            label='manifest' if p[0]==3 else ['BG','OBJ','map','CGRAM','OAM','HDMA'][p[1]]
            sections[label]+=len(p)-16;packets[label]+=1
        self.rows.append({'frame':args[2],'bank':self.bank,'raw_rows':count,'section_body_B':dict(sections),'section_packets':dict(packets),
                          'E1_wire_B':sum(len(p)+3 for p in self.packets),'target_instructions':sum(self.function_counts.values()),
                          'function_instructions':dict(self.function_counts),'canonical_state_SHA256':self.canonical_state_SHA256,
                          'expired_BG_scratch_mutated':after!=snapshot,'outside_expired_scratch_equal':True,
                          'canonical_HDMA_SHA256':hashlib.sha256(expected).hexdigest()})
        return 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','dataset','reference','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--last',type=int,default=975)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    ref=json.loads((a.reference/'result.json').read_text());nums=map(int,re.search(r'\{(.*?)\}',(a.arm/'nes_palette165.inc').read_text(),re.S)[1].split(','));m=CompactAudit(a.arm,struct.pack('<64H',*nums),a.out)
    inputs={}
    for serial,frame in enumerate(range(905,a.last+1),1):
        paths=[a.dataset/f'frame{frame}.{ext}' for ext in ['geometry','raw']]
        for q in paths:assert sha(q)==ref['input_sha256'][q.name];inputs[q.name]=sha(q)
        geometry,raw=[q.read_bytes() for q in paths];packets,_,_=encode(geometry,raw,frame)
        actual=m.frame(packets,geometry,raw,frame,serial)
        prior=json.loads((a.reference/f'frame{frame}.json').read_text())['candidate']
        assert m.canonical_state_SHA256==prior['state_sha256'] and actual['plans']==prior['plans']
        (a.out/f'frame{frame}'/'plans.json').write_text(json.dumps(actual['plans']))
        print(json.dumps({'frame':frame,'wire':m.rows[-1]['E1_wire_B'],'instructions':m.rows[-1]['target_instructions']}),flush=True)
    result={'passed':True,'scope':__doc__,'firmware_SHA256':sha(a.arm/'obj-nes-100/firmware.stm'),'input_SHA256':inputs,'frames':m.rows,
            'canonicalized_state_and_actual_plans_equal':True,'only_expired_BG_scratch_mutated':True,'hardware_time':False}
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
