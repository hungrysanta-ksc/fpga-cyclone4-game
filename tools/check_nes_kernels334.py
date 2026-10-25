# SPDX-License-Identifier: MIT
"""Execute actual M4 CRC and span selection against independent oracles."""
import argparse,binascii,json,random
from pathlib import Path
from probe_nes_native289 import Producer
from nes_delta231 import sha


def reference(b):
    def repeat(p):
        n=min(len(p),4096);i=2
        while i+1<n and p[i]==p[0] and p[i+1]==p[1]:i+=2
        return 0 if n<2 else i
    r=repeat(b)
    if r>=64:return r
    end=min(len(b),240)
    return next((i for i in range(1,end) if repeat(b[i:])>=64),end)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    arm=Producer(a.source/'output.elf',None);rng=random.Random(334)
    crc_inputs=[(c,b) for c in (0,65535,0x1234,0x8000) for b in range(256)]
    crc_inputs += [(rng.randrange(65536),rng.randrange(256)) for _ in range(4096)]
    for c,b in crc_inputs:assert arm.call('crc16',[c,b])==binascii.crc_hqx(bytes((b,)),c),(c,b)
    vectors=[]
    for n in (1,2,3,62,63,64,65,127,128,239,240,241,302,303,304,511,544,1121,4096):
        vectors.extend([bytes(n),bytes(i%2 for i in range(n)),bytes(rng.randrange(256) for _ in range(n))])
    for start in range(241):
        for run in (62,63,64,65,80):
            b=bytearray((i*73+11)&255 for i in range(400))
            b[start:start+run]=bytes(i%2 for i in range(run))
            vectors.append(bytes(b))
    for _ in range(300):
        n=rng.randrange(1,4097);vectors.append(bytes(rng.randrange(4) for _ in range(n)))
    for i,b in enumerate(vectors):
        arm.uc.mem_write(0x20028000,b)
        got=arm.call('span_piece',[0x20028000,len(b)])
        assert got==reference(b),(i,len(b),got,reference(b))
    result=dict(passed=True,CRC_cases=len(crc_inputs),span_cases=len(vectors),instructions=arm.instructions,
        ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),scope=__doc__)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))


if __name__=='__main__':main()
