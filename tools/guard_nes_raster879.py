"""Compare all 951 data blocks and rejected partial inputs on both linked receivers."""
import argparse
import hashlib
import json
from pathlib import Path

from check_nes_game478 import Machine


def check(sender, work):
    machines = [Machine(src/'link-credit/src',bytes(128)) for src in
                (work.parent/'nes-retire878-finish',work)]
    blocks = [bytes.fromhex(r['wire']) for r in json.loads(sender.read_bytes())['951']]
    target = blocks[-3]
    assert len(target)==117 and target[22:24]==bytes.fromhex('fcb7') and target[-12:-10]==bytes.fromhex('e004')
    def reset():
        for c in machines:
            c.call('nes_native165_reset',[c.state])
    def send(token, block, expected):
        snapshots=[]
        for c in machines:
            ptr=c.lut+256
            c.u.mem_write(ptr,block)
            ok=c.call('nes_native165_packet',[c.state,token,ptr,len(block)])
            assert bool(ok)==expected,(token,ok)
            snapshots.append(bytes(c.u.mem_read(c.state,c.layout['nes_native165']['size'])))
        assert snapshots[0]==snapshots[1]
        return hashlib.sha256(snapshots[0]).hexdigest()
    def prefix():
        reset()
        return [send(i,b,True) for i,b in enumerate(blocks[:-3])]
    def full():
        rows=prefix()
        rows.extend(send(i,b,True) for i,b in enumerate(blocks[-3:-1],len(rows)))
        return rows
    hashes=full()
    failures={}
    for name,ix,mask in [('oversized_run',23,0x40),('raw_first_row',27,2),('wrong_record_count',114,1)]:
        prefix()
        block=bytearray(target)
        block[ix]^=mask
        failures[name]=send(len(blocks)-3,bytes(block),False)
        assert full()==hashes
    prefix()
    failures['truncated_metadata']=send(len(blocks)-3,target[:-1],False)
    assert full()==hashes
    prefix()
    send(len(blocks)-3,target,True)
    assert full()==hashes
    return dict(block_sha256=hashlib.sha256(target).hexdigest(), before_COMMIT=hashes,
                rejected=failures, reset_after_partial=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('sender','work','out'):
        p.add_argument(key,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(check(a.sender,a.work),indent=2)+'\n')
