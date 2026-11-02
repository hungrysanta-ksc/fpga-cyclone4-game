# SPDX-License-Identifier: MIT
"""Replay three generation-954 E9 batches on the board SPI, RAM and actual CDC."""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess

from test_nes_raw506_joint import crc,wire_plan
from nes_raw506 import sha


def run(a):
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    a.out.mkdir(parents=True,exist_ok=False)
    plans=[bytes.fromhex(h) for _,h in json.loads((a.plans/'frame954/plans.json').read_text())]
    assert len(plans)==23
    plans.append(struct.pack('<HHHBB',954,0,0,3,0)+bytes(16)+b'\xff'*16)
    records=[]
    # The 549 sender sorts contiguous compact OBJ subsequences. Frame 954's
    # recorded OBJ slots are already ascending; verify the actual output below.
    for start,end in ((0,4),(4,19),(19,24)):
        body=b''.join(wire_plan(q) for q in plans[start:end])
        b=bytes([0xe9,len(body),len(body)>>8,end-start])+body+crc(body,16,0x1021,65535).to_bytes(2,'big')
        records.append(b+bytes([crc(b,8,7,0),0xa5]))
    assert [len(b) for b in records]==[32,121,43]
    (a.out/'requests.hex').write_text('\n'.join(f'{b:02x}' for b in b''.join(records))+'\n')
    exp=[]
    for q in plans[:-1]:
        _,s,t,k,m=struct.unpack_from('<HHHBB',q)
        exp.append(f'{k<<31|s<<21|t<<8|m:09x}')
    (a.out/'plans.hex').write_text('\n'.join(exp)+'\n')
    modules=['nes_domain_reset124','nes_native_mailbox206','nes_plan_batch206','nes_plan_spi200']
    pins=json.loads((a.board/'inputs535.json').read_text())
    files=[a.board/(n+'.sv') for n in modules]
    assert all(sha(f)==pins[f.name] for f in files)
    def command(tool,args,name):
        with (a.out/(name+'.log')).open('wb') as log:
            subprocess.run([str(a.bin/(tool+'.exe')),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,
                           timeout=120,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    command('vlib',['work'],'lib')
    command('vlog',['-sv',*map(str,files),str(Path(__file__).resolve().parents[1]/'tests/nes-functional/plan_credit557_tb.sv')],'compile')
    for phase in (0,11000):
        name=f'phase{phase}'
        command('vsim',['-c','-voptargs=+acc','plan_credit557_tb','+PHASE='+str(phase),'-do','run -all; quit -f'],name)
        assert 'PASS BANK557' in (a.out/(name+'.log')).read_text(errors='replace')
    (a.out/'result.json').write_text(json.dumps(dict(phases_ps=[0,11000],board_modules={f.name:sha(f) for f in files},
        requests=[b.hex() for b in records],source='board SPI + plan transport + CDC, held tile completion, zero chunk descriptor'),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('board','plans','bin','out'):p.add_argument('--'+k,required=True,type=Path)
    a=p.parse_args();a.board=a.board.resolve();a.out=a.out.resolve();run(a)
