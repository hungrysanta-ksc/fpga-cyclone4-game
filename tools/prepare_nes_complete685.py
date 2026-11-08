"""Complete one accepted map range only with the fresh early-VBlank budget."""
import argparse,json
from pathlib import Path
from build_nes_trace_replay import Code
from prepare_nes_progress680 import client,ORIGIN
from prepare_nes_late681 import receiver
from nes_raw506 import sha

def edit(body,labels):
    body,labels=receiver(body,labels,True)
    assert sha_bytes(body)=='d623c2b34e68a6a6c6b51d03daffc960c8bb1bc8e36b3cf816e2b12e050a48c9'
    body=bytearray(body);tail=Code(ORIGIN+len(body));tail.labels.update(labels)
    tail.label('complete685')
    # Only a complete <=1536B accepted range can exceed the old1152B cap.
    # Partial retirement therefore retains the original1152B arithmetic.
    tail.emit(0xc2,0x20);tail.long(0xbf,0x7e4004);tail.emit(0xc9,1,6)
    tail.branch(0xb0,'keep_cap685');tail.emit(0xa8)
    tail.label('keep_cap685');tail.emit(0xe2,0x20);tail.jump('map_beam_ok526')
    c=Code(labels['selected526']);c.labels.update(tail.labels)
    defer='defer_beam'
    c.emit(0xe2,0x20);c.absolute(0xad,0x4212);c.branch(0x10,defer)
    c.absolute(0xad,0x213f);c.absolute(0xad,0x213f);c.emit(0x89,0x40);c.branch(0xd0,defer)
    c.absolute(0xad,0x2137);c.absolute(0xad,0x213f);c.emit(0x89,0x40);c.branch(0xf0,defer)
    c.absolute(0xad,0x213d);c.emit(0xeb);c.absolute(0xad,0x213d);c.emit(0x29,1);c.branch(0xd0,defer)
    c.emit(0xeb,0xc9,225);c.branch(0x90,defer)
    # wait169 initializes103E before either loop and runs only after SEAL.
    # Idle prefix cannot nest that wait; reuse its dead low byte, no new RAM.
    c.absolute(0x8d,0x103e)
    c.emit(0xc9,233);c.branch(0x90,'budget685')
    c.emit(0xc9,253);c.branch(0xb0,defer)
    c.long(0xbf,0x7e4001);c.emit(0x29,0x70,0xc9,0x50);c.branch(0xf0,'budget685')
    c.jump('late_map680')
    c.label('budget685');c.absolute(0xad,0x103e);c.emit(0xc9,249);c.branch(0xb0,'map_beam_ok526')
    c.long(0xbf,0x7e4001);c.emit(0x29,0x70,0xc9,0x50);c.branch(0xd0,'map_beam_ok526')
    c.jump('complete685')
    new=c.finish();lo=labels['selected526']-ORIGIN;hi=labels['map_beam_ok526']-ORIGIN
    assert len(new)<=hi-lo,(len(new),hi-lo)
    body[lo:hi]=new+bytes([0xea])*(hi-lo-len(new))
    # The late interior search uses the same fresh sample and shared cap.
    at=labels['length_map680']-ORIGIN+3
    assert body[at:at+3]==bytes([0x4c])+(labels['map_beam_ok526']&65535).to_bytes(2,'little')
    body[at:at+3]=bytes([0x4c])+(c.labels['budget685']&65535).to_bytes(2,'little')
    body.extend(tail.finish());assert len(body)<=5984
    labels.update(c.labels);labels.update(tail.labels)
    return body,labels

def sha_bytes(b):
    from hashlib import sha256
    return sha256(b).hexdigest()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    info=client(a.base,a.out,extra_edit=edit)
    info.update(candidate='complete685',complete_map_max_B=1536,complete_last_latch_line=248,
        late_map_max_B=1152,last_map_latch_line=252,new_WRAM_B=0,reused_dead_wait_counter='103E low',
        STOP_and_new_head_checked_before_DMA=True,partial_retirement_bytes_unchanged=1152)
    (a.out/'build.json').write_text(json.dumps(info,indent=2)+'\n')
    print(json.dumps({k:info[k] for k in ('body_bytes','body_free','prefix_B','physical_free_B')}))
