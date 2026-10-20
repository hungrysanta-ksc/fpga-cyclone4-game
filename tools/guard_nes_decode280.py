# SPDX-License-Identifier: MIT
"""Cortex-M4 N5-v2 CRC/order/cold/STOP and raw count transition guards."""
import argparse,binascii,json,shutil
from pathlib import Path
from probe_nes_decode280 import ARM,sha,golden,encode280,chunks


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--arm',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    shutil.copyfile(a.arm/'decoder.elf',d/'decoder.elf');arm=ARM(d/'decoder.elf',None)
    geom,raw=golden(905);rr=encode280(bytes(4398),geom,raw,None,1,65535)
    def run(records,bad_crc=False):
        ok=1
        for b in chunks(records):
            arm.uc.mem_write(0x20018000,b)
            ok=arm.call('block280',[0x20010000,0x20018000,len(b),binascii.crc_hqx(b,65535)^bad_crc])
            if not ok:break
        return bool(ok and arm.call('complete280',[]))
    rejects=[]
    def fail(name,rs,crc=False):
        arm.call('reset280',[]);assert not run(rs,crc),name
        assert arm.call('complete280',[])==0
        rejects.append(name)
    def mutate(i,off,value):
        rows=list(rr);r=bytearray(rows[i]);r[off]=value;rows[i]=bytes(r);return rows
    fail('transport CRC',rr,True)
    fail('N5 version',mutate(0,2,1))
    fail('cold flag absent',mutate(0,3,0))
    fail('unknown flags',mutate(0,3,7))
    fail('cold prior serial',mutate(0,8,1))
    fail('zero epoch',mutate(0,4,0))
    fail('reserved header',mutate(0,18,1))
    fail('missing first geometry block',[rr[0]]+rr[2:])
    fail('duplicate geometry block',rr[:2]+[rr[1]]+rr[2:])
    fail('cold shift',mutate(1,0,128))
    gi=next(i for i,r in enumerate(rr) if r[:4]==b'\xff\xff\x00\x03')
    fail('geometry span mismatch',mutate(gi,4,0))
    fail('geometry CRC',mutate(gi,8,0))
    fail('raw block missing',rr[:gi+1]+rr[gi+2:])
    fail('raw duplicate',rr[:gi+2]+[rr[gi+1]]+rr[gi+2:])
    fail('raw index outside 512',mutate(gi+1,0,76))
    fail('raw value not six bits',mutate(gi+1,9,64))
    fail('raw mask empty',rr[:gi+1]+[bytes([68])+bytes(8)]+rr[gi+2:])
    fail('frame CRC',mutate(len(rr)-1,4,rr[-1][4]^1))
    fail('trailing record',rr+[bytes([68])+b'\1'+bytes(7)+b'\0'])
    # ARM transition source history, not display-bank history. Generation
    # wrap does not reset source serial; raw count changes require full raw.
    arm.call('reset280',[]);assert run(rr)
    prior=geom;prior_raw=raw;transitions=[]
    for serial,count in [(2,0),(3,2),(4,1),(5,2)]:
        g=bytearray(geom);g[-1]=count;r=raw[:count*256]
        x=encode280(prior,bytes(g),r,prior_raw,serial,(serial-2)&65535)
        assert run(x),(serial,count)
        assert bytes(arm.uc.mem_read(0x20010000,4398+len(r)))==bytes(g)+r
        transitions.append(dict(serial=serial,raw=count,generation=(serial-2)&65535))
        prior=bytes(g);prior_raw=r
    warm=encode280(prior,prior,prior_raw,prior_raw,6,4)
    arm.call('reset280',[]);assert not run(warm);rejects.append('STOP then stale warm')
    # Warm count change with a syntactically correct header but no raw-cold
    # bit is rejected at the geometry boundary before old raw can be reused.
    arm.call('reset280',[]);assert run(rr)
    g=bytearray(geom);g[-1]=0;x=encode280(geom,bytes(g),b'',raw,2,0)
    h=bytearray(x[0]);h[3]&=~2;x[0]=bytes(h)
    # Recompute all frame CRCs so the count guard is exercised.
    c=65535
    for i,r in enumerate(x):
        trailer=r[:4] in (b'\xff\xff\x00\x03',b'\xff\xff\x00\x04')
        c=binascii.crc_hqx(r[:-2] if trailer else r,c)
        if trailer:x[i]=r[:-2]+c.to_bytes(2,'little')
    assert not run(x);rejects.append('count change without raw cold')
    result=dict(passed=True,rejects=rejects,transitions=transitions,ELF_sha256=sha(d/'decoder.elf'),scope=__doc__)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
