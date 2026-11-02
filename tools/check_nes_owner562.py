# SPDX-License-Identifier: MIT
"""Pin-level loader/reader differential replay with the two 561 grant schedules."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
from nes_raw506 import sha


def vectors(folder,plans):
    phases=json.loads((folder/'obj-phases.json').read_text())
    vectors=[]
    for g in (952,954):
        raw=[bytes.fromhex(h) for _,h in json.loads((plans/f'frame{g}/plans.json').read_text())]
        bg=[q for q in raw if q[6]==0]
        obj={int.from_bytes(q[2:4],'little'):q for q in raw if q[6]==1}
        slots=[q['slot'] for q in phases[str(g)]['obj_plans']]
        assert set(slots)==set(obj) and len(slots)==len(obj)
        reads=iter(phases[str(g)]['rom_service'])
        for q in bg+[obj[s] for s in slots]:
            _,_,tag,kind,mask=struct.unpack_from('<HHHBB',q)
            for i in range(16):
                if kind and not mask&(1<<(i//2)):continue
                alt=int.from_bytes(q[24+(i//2)*2:26+(i//2)*2],'little')
                bank=alt if not i%2 and alt!=65535 else tag
                address=(bank<<4)|((i%2)<<3)|q[8+i]
                k,_,grant,_=next(reads)
                assert k==kind and 0<=address<131072
                vectors.append((int(grant),0x40000+address))
        assert next(reads,None) is None
    return [(t-vectors[0][0],p) for t,p in vectors]


def pin_model(bench):
    model=(bench/'rom_boot_model.sv').read_text()
    for small,full in [('65535','262143'),('32767','131071'),("24'h10000","24'h40000"),
                       ("24'h208000","24'h220000"),('a[15:0]','a[17:0]'),('a[14:0]','a[16:0]')]:
        assert small in model
        model=model.replace(small,full)
    return model


def run(a):
    bench=Path(__file__).resolve().parents[1]/'tests/nes-functional'
    a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'pins.sv').write_text(pin_model(bench),newline='\n')
    stimuli=[(bench/f'owner562-reads{i}.txt').read_text(encoding='ascii') for i in (1,2)]
    if a.traces is not None:
        for i,s in enumerate(stimuli,1):
            vec=vectors(a.traces/f'nes-close561-run{i}',a.plans)
            assert s==''.join(f'{t} {v}\n' for t,v in vec)
    traces={}
    for name,board in [('ref',a.base),('new',a.board)]:
        d=a.out/name;d.mkdir()
        def execute(tool,args,label):
            with (d/(label+'.log')).open('wb') as log:
                subprocess.run([str(a.bin/(tool+'.exe')),*map(str,args)],cwd=d,stdout=log,stderr=subprocess.STDOUT,
                               check=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
            return (d/(label+'.log')).read_text(errors='replace')
        execute('vlib',['work'],'lib')
        files=[board/('nes_'+n+'.sv') for n in ('domain_reset124','native_ciram165','local_memory','rom_loader','rom_physical','rom_boot')]
        execute('vlog',['-sv',*(['+define+OWNER562'] if name=='new' else []),*files,a.out/'pins.sv',bench/'owner562_tb.sv'],'compile')
        counts=[len(s.splitlines()) for s in stimuli]
        for i,s in enumerate(stimuli,1):
            (d/f'reads{i}.txt').write_text(s)
        args=['-c','owner562_tb','-do','run -all; quit -f']
        smoke=execute('vsim',[*args,'+SMOKE'],'smoke')
        assert f'PASS562 phase=2 total_reads={sum(counts)} scrubs=4 writes=2' in smoke,(name,'smoke')
        s=execute('vsim',args,'run')
        for i in (1,2):
            assert f'PASS562 phase={i} total_reads={sum(counts[:i])} scrubs={2*i} writes=393216' in s,(name,i)
            section=s.split(f'# PHASE562 {i}\n')[1].split('# PASS562')[0]
            events=[l[2:] for l in section.splitlines() if l.startswith(('# ACCEPT562 ','# REPLY562 '))]
            assert len(events)==2*(counts[i-1]+2)+1
            f=d/f'bus{i}.txt';f.write_text('\n'.join(events)+'\n')
            traces[f'{name}{i}']=dict(bus=sha(f),input=sha(d/f'reads{i}.txt'),events=len(events),reads=counts[i-1])
    for i in (1,2):assert traces[f'ref{i}']==traces[f'new{i}']
    (a.out/'result.json').write_text(json.dumps(traces,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','board','bin','out'):p.add_argument('--'+k,type=Path,required=True)
    for k in ('plans','traces'):p.add_argument('--'+k,type=Path)
    a=p.parse_args()
    if (a.traces is None)!=(a.plans is None):p.error('supply both --traces and --plans to verify fixture provenance')
    run(a)
