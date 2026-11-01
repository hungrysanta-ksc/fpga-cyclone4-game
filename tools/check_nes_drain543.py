# SPDX-License-Identifier: MIT
"""Execute the linked post-map drain; fixture map emission and stop before palette data."""
import argparse
import json
from pathlib import Path
from check_nes_supply485_arm import ARM, Endpoint, crc, sha
from check_nes_game478 import UC_ARM_REG_R0, UC_ARM_REG_PC, UC_ARM_REG_LR


class Status(Endpoint):
    def __init__(self,mode):
        super().__init__('normal')
        self.test_mode=mode;self.live=False;self.polls=0
    def exchange(self,tx,clock):
        if not self.live:return super().exchange(tx,clock)
        assert tx[0]==0xe0,tx.hex()
        self.calls.append(tx.hex());self.polls+=1
        if self.test_mode!='timeout' and self.polls>=3:self.retired=self.sent
        r=bytearray(20);used=(self.sent-self.retired)&65535
        r[1:3]=bytes([0xf7,int(used>0)|2])
        r[3:5]=self.sent.to_bytes(2,'big');r[5:7]=self.retired.to_bytes(2,'big');r[7:19]=self.last
        if self.test_mode=='bad_identity' and not used:r[9]^=1
        if self.test_mode=='bad_status' and not used:r[7]^=1
        if self.test_mode=='bad_counter':r[5:7]=((self.sent+1)&65535).to_bytes(2,'big')
        r[19]=crc(r[1:19],8,7,0)
        if self.test_mode=='bad_crc':r[19]^=1
        if self.test_mode=='STOP':self.mode='STOP_after_E9';self.accepted=1
        return bytes(r)


class Probe(ARM):
    def __init__(self,src,mode):
        self.live_probe=False;self.map_called=0;self.after_drain=False
        super().__init__(src,mode)
    def hook(self,u,at,size,user):
        syms=getattr(self,'syms',{})
        if self.live_probe and at in (syms.get('map527'),syms.get('span')):
            if at==syms['map527']:self.map_called+=1;result=1
            else:self.after_drain=True;result=0  # Deliberate downstream stop; no SEAL/commit.
            u.reg_write(UC_ARM_REG_R0,result);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        super().hook(u,at,size,user)


def check(src,mode):
    m=Probe(src,mode);m.endpoint=ep=Status(mode);m.setup()
    for ptr,kind in ((m.resident,'nes_resident211'),(m.video,'nes_native_video165')):
        m.u.mem_write(ptr,bytes(m.layout[kind]['size']))
    for field,value,n in [('serial',1,4),('generation',907,2),('prepared',1,1),('open',1,1),('map_upload',int(mode!='empty'),8)]:
        m.put(m.resident,'nes_resident211',field,value,n)
    for field,value,n in [('generation',907,2),('valid',1,1),('bg_count',1,2),('hdma_size',1,2),('display_mask',0x1e,1)]:
        m.put(m.video,'nes_native_video165',field,value,n)
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    ep.sent=1 if mode=='wrap' else 2;ep.retired=65535 if mode=='wrap' else 0
    head=bytes([2,2,1,0,1,0,0,0,139,3]);ep.last=b'\0\2'+head[2:10]+b'\x65\x9a'
    for field,value,n in [('sent',ep.sent,2),('retired',ep.retired,2),('ever_sent',1,1),('poll_limit',8,4)]:
        m.put(m.w,'nes_sink_window184',field,value,n)
    m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],head)
    ep.calls.clear();ep.live=True;m.live_probe=True
    assert m.call('nes_sink212_seal',[m.s,m.video,m.resident])==0
    assert m.map_called==1
    assert m.after_drain==(mode in ('normal','wrap','empty')),(mode,m.after_drain)
    assert not m.get(m.s,'nes_native_sink165','displayed')
    assert m.get(m.resident,'nes_resident211','open')==1
    assert ep.polls==({'normal':3,'wrap':3,'empty':0,'timeout':8,'bad_identity':3,'bad_status':3}.get(mode,1))
    return dict(case=mode,polls=ep.polls,ordinary_checkpoint=m.after_drain,
                window_error=m.get(m.w,'nes_sink_window184','error'),final_commit=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();rows=[check(a.arm,k) for k in ('normal','wrap','empty','bad_crc','bad_identity','bad_status','bad_counter','STOP','timeout')]
    a.out.write_text(json.dumps(dict(scope=__doc__,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),rows=rows),indent=2)+'\n')
