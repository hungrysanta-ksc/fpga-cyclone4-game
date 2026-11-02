# SPDX-License-Identifier: MIT
"""Feed the four retimed 954 E8/E9 sequences to the pinned board RTL, using external tile finish stimuli."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

from analyze_nes_phase537 import read,sha
from test_nes_raw506_joint import MASTER,ARM_HZ


def fixture(folder,plans,out):
    phase=read(folder/'obj-phases.json')['954']
    batches=phase['banks557']
    events=[r for r in read(folder/'events.json') if r['generation']==954 and r.get('opcode') in ('0xe8','0xe9')
            and r['clock']<=phase['end_accepted']]
    origin=events[0]['start']-100
    ticks=lambda t:round((t-origin)*1e12/MASTER)
    lines=[];off=0
    for row in events:
        op=int(row['opcode'],16);n=row['bytes']
        flag=bytes.fromhex(row['reply'])[3] if op==232 else 0
        lines.append(f"{ticks(row['start'])} {ticks(row['clock'])} {op} {off} {n} {flag}")
        if op==233:off+=n
    assert off==196 and [b['count'] for b in batches]==[4,15,5]
    (out/'spi.dat').write_text('\n'.join(lines)+'\n')
    service=iter(phase['rom_service']);finishes=[]
    for _,h in read(plans/'frame954/plans.json'):
        q=bytes.fromhex(h);kind=q[6];size=32 if kind==1 else 16
        if kind==2:
            assert not finishes
            returned=batches[0]['first_check']+1
        else:
            for _ in range(2*q[7].bit_count()):
                k,_,_,returned=next(service)
                assert k==kind
        finishes.append(ticks(returned+size*4+math.ceil((2*size+8)*MASTER/ARM_HZ)))
    assert next(service,None) is None and len(finishes)==23
    (out/'done.dat').write_text('\n'.join(map(str,finishes))+'\n')
    return len(lines)-3


def run(a):
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    a.out.mkdir(parents=True,exist_ok=False)
    board=a.board.resolve();direct=read(a.direct/'result.json')
    files=[board/n for n,h in direct['board_modules'].items()]
    assert all(sha(f)==direct['board_modules'][f.name] for f in files)
    def call(tool,args,out,name):
        with (out/(name+'.log')).open('wb') as log:
            subprocess.run([str(a.bin/(tool+'.exe')),*args],cwd=out,stdout=log,stderr=subprocess.STDOUT,
                           check=True,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
    result={}
    for mode in ('base','probe'):
        for i in (1,2):
            folder=a.traces/f'nes-end557-banks-{mode}{i}'
            d=a.out/(mode+str(i));d.mkdir()
            call('vlib',['work'],d,'lib')
            call('vlog',['-sv',*map(str,files),str(Path(__file__).resolve().parents[1]/'tests/nes-functional/plan_credit557_tb.sv')],d,'compile')
            for n in ('requests.hex','plans.hex'):shutil.copyfile(a.direct/n,d/n)
            count=fixture(folder,a.plans,d)
            for early in (0,1):
                name='nominal' if not early else 'wire-only'
                call('vsim',['-c','-voptargs=+acc','plan_credit557_tb','+TIMED',
                             '+PHASE='+str((i-1)*11000),'+EARLY='+str(early),'-do','run -all; quit -f'],d,name)
                log=(d/(name+'.log')).read_text(errors='replace')
                assert f'E8={count} plans=23' in log and 'PASS TIMED557' in log,(d,name)
            result[d.name]=dict(E8=count,E9=3,plans=23,seal_placements=2,spi=sha(d/'spi.dat'),done=sha(d/'done.dat'))
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('board','direct','traces','plans','bin','out'):p.add_argument('--'+n,required=True,type=Path)
    a=p.parse_args();run(a)
