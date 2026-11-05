"""Exercise linked one-credit enqueue, wrap, corrupt ACK and STOP before reuse."""
import argparse
import json
from pathlib import Path
import struct
from check_nes_supply485_arm import ARM,crc,sha


def check(src,mode,wrap=False):
    m=ARM(src,'normal')
    state=dict(sent=0,retired=0,polls=0,packets=0,last=bytes(12),body=None)
    def exchange(tx,clock):
        if tx[0]==0xe1:
            assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
            assert state['sent']==state['retired']
            state['body']=tx[1:-2];state['sent']=(state['sent']+1)&65535
            state['packets']+=1;state['polls']=0
            return bytes(len(tx))
        assert tx[0]==0xe0
        pending=state['sent']!=state['retired']
        if pending:
            state['polls']+=1
            if mode=='STOP' and state['polls']==1:
                m.endpoint.mode='STOP_after_bulk';m.endpoint.bulk=1
            if state['polls']==3:
                state['retired']=state['sent'];pending=False
                b=state['body'];state['last']=bytes([0,b[0]])+b[2:10]+b'\x65\x9a'
        reply=bytearray(20);reply[1]=0xf7
        reply[2]=int(pending)|(2 if state['retired'] or state['last'][1] else 0)
        reply[3:7]=struct.pack('>HH',state['sent'],state['retired'])
        reply[7:19]=state['last']
        if mode=='identity' and state['last'][1]:reply[9]^=1
        if mode=='count' and state['packets']:reply[4]^=1
        reply[-1]=crc(reply[1:19],8,7,0)
        if mode=='CRC' and state['packets']:reply[-1]^=1
        return bytes(reply)
    m.endpoint.exchange=exchange;m.setup()
    if wrap:
        state['sent']=state['retired']=65535
        m.put(m.w,'nes_sink_window184','sent',65535,2)
        m.put(m.w,'nes_sink_window184','retired',65535,2)
    success=True
    for i in range(3):
        b=bytearray(18);b[0]=2;b[1]=2;b[2:4]=i.to_bytes(2,'little')
        b[4:8]=(1).to_bytes(4,'little');b[8:10]=(907).to_bytes(2,'little')
        b[12]=2;b[16:]=bytes([i,i])
        m.u.mem_write(m.q,bytes(b))
        success=bool(m.call('nes_window184_enqueue',[m.w,m.q,len(b)]))
        if not success:break
    enqueued=success
    if success:
        success=bool(m.call('nes_window184_drain',[m.w,m.q+64]))
    assert success==(mode=='normal'),(mode,state,m.get(m.w,'nes_sink_window184','error'))
    assert state['packets']==(3 if enqueued else 1)
    assert not m.get(m.s,'nes_native_sink165','displayed')
    return dict(mode=mode,wrap=wrap,success=success,packets=state['packets'],
                window_error=m.get(m.w,'nes_sink_window184','error'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    rows=[check(a.arm,mode) for mode in ('normal','CRC','identity','count','STOP')]
    rows.append(check(a.arm,'normal',True))
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),rows=rows),indent=2)+'\n')
