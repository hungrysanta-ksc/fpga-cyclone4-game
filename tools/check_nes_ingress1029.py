"""Exercise completion ownership on the linked receiver including ARM counter wrap."""
import struct
from check_nes_frame862_arm import TimedProbe
from read_nes_ingress1029 import INGRESS, OFFSET


def trace_test(src,edition):
    m=TimedProbe(src)
    m.call('nes_budget210_reset',[])
    cache=m.data['ptrcache']
    def entry(i):
        return INGRESS.unpack(bytes(m.u.mem_read(cache+OFFSET+i*INGRESS.size,INGRESS.size)))
    ptr=0x20012000
    def block(begin,g,n,stamps):
        m.u.mem_write(ptr,struct.pack('<4I',*stamps))
        m.call('block1029',[begin,g,n,ptr])
    block(0,71,4,[10,11,16,20])
    assert not entry(82)[-1]
    block(1,71,192,[0xffffffe0,0xfffffff0,1,5])
    block(0,71,12,[11,20,32,44])
    expected=(0xffffffe0,44,25,29,16,204,71,2)
    assert entry(82)==expected
    m.call('input900',[71])
    assert entry(81)==expected and not entry(82)[-1]
    block(1,73,40,[55,60,75,88])
    m.call('input900',[73])
    assert entry(81)==expected and entry(80)[-2:]==(73,1)
    m.put(m.video,'nes_native_video165','generation',71,2)
    m.u.mem_write(m.data['mode900'],bytes([3]))
    m.call('e0900',[71,0])
    m.call('nes_budget210_frame',[4361])
    m.call('nes_budget210_display',[4361,m.video])
    assert entry(0)==expected
    m.call('nes_budget210_reset',[])
    assert not any(entry(i)[-1] for i in (0,80,81,82))
    return dict(reset=True,wrapped_counter=True,two_pending_generations=True,
                checked_row_copy=True,ignored_unstarted=True)
