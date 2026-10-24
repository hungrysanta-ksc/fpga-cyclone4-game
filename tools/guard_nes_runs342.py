# SPDX-License-Identifier: MIT
"""Actual M4 decoder rejection/cold recovery, with rechecked block CRC."""
import argparse,binascii,json
from pathlib import Path
from nes_delta231 import sha
from probe_nes_arm264 import ARM
from probe_nes_decode280 import records,chunks,golden

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--arm',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    assert not a.out.exists();a.out.mkdir(parents=True)
    arm=ARM(a.arm/'decoder.elf',None);rr=records(a.arm/'frame905.records')
    geo=next(i for i,r in enumerate(rr) if r[:4]==b'\xff\xff\0\3')
    region=next(i for i,r in enumerate(rr) if 64<=r[0]<=72)
    raw=next(i for i,r in enumerate(rr) if r[0]==72)
    raster=next(i for i,r in enumerate(rr) if r[0]==67)
    cases=[]
    def case(name,index,edit):
        r=list(rr);r[index]=edit(bytearray(r[index]));cases.append((name,r))
    def setbyte(b,i,v):b[i]=v;return bytes(b)
    case('legacy-version',0,lambda b:setbyte(b,2,2))
    case('future-version',0,lambda b:setbyte(b,2,5))
    case('invalid-region',region,lambda b:setbyte(b,0,73))
    case('truncated-map-offset',region,lambda b:bytes(b[:1]+b'\0\x08'+b[3:]))
    case('cold-gap',region,lambda b:setbyte(b,1,1))
    case('range-overflow',region,lambda b:bytes(b[:1]+b'\xff\xff'+b[3:]))
    case('bad-mode',region,lambda b:setbyte(b,3,192))
    case('pair-on-byte-region',region,lambda b:setbyte(b,3,129))
    case('odd-pair',raster,lambda b:setbyte(b,3,128))
    case('GEO-count',geo,lambda b:setbyte(b,4,b[4]^1))
    case('GEO-CRC',geo,lambda b:setbyte(b,9,b[9]^1))
    case('raw-out-of-range',raw,lambda b:setbyte(b,4,64))
    case('final-CRC',len(rr)-1,lambda b:setbyte(b,5,b[5]^1))
    cases.append(('duplicate-region-record',rr[:region+1]+[rr[region]]+rr[region+1:]))
    cases.append(('missing-cold-region',rr[:region]+rr[region+1:]))
    cases.append(('early-final',rr[:geo+1]+[rr[-1]]))
    results=[]
    def feed(recs):
        for b in chunks(recs):
            arm.uc.mem_write(0x20018000,b)
            if not arm.call('block280',[0x20010000,0x20018000,len(b),binascii.crc_hqx(b,65535)]):return False
        return bool(arm.call('complete280',[]))
    for name,recs in cases:
        arm.call('reset280',[]);assert not feed(recs),name
        assert not arm.call('complete280',[]),name
        # Failed state is sticky until STOP/reset; fresh cold frame recovers.
        assert not feed(rr),name
        arm.call('reset280',[]);assert feed(rr),name
        g,r=golden(905);assert bytes(arm.uc.mem_read(0x20010000,4910))==g+r
        results.append(dict(name=name,rejected=True,cold_recovery=True))
    out=dict(passed=True,cases=results,ELF_sha256=sha(a.arm/'decoder.elf'),scope='Actual M4 source decoder; not RTL STOP/final display ACK')
    (a.out/'result.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS',len(results),'actual M4 guards + sticky failure/cold recovery')
if __name__=='__main__':main()
