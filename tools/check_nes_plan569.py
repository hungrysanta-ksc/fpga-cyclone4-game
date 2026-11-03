# SPDX-License-Identifier: MIT
"""Run board SPI batches and inspect the decoder's capture, ACK and bank reuse."""
import argparse
import json
from pathlib import Path
import subprocess
from nes_raw506 import once,sha
from replay_nes_banks557_rtl import fixture


def run(args):
    bench=Path(__file__).resolve().parents[1]/'tests/nes-functional'
    evidence=json.loads((bench.parents[1]/'analysis/end557-verification.json').read_text())['directed_RTL']
    expected=args.fixtures/'plans.hex'
    assert sha(expected)=='3c501203ace52bede32dbca9ed043835cc7a6444a66d8fbd3846da1f3f180f8d'
    payload=b''.join(bytes.fromhex(r) for r in evidence['requests'])
    result={};reference={}
    args.out.mkdir(parents=True,exist_ok=False)
    for name,board in [('reference',args.base),('direct',args.board)]:
        d=args.out/name;d.mkdir()
        def execute(tool,argv,label):
            p=d/(label+'.log')
            with p.open('wb') as f:
                subprocess.run([str(args.bin/(tool+'.exe')),*map(str,argv)],cwd=d,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=120)
            return p.read_text(errors='replace')
        (d/'requests.hex').write_text(''.join(f'{b:02x}\n' for b in payload))
        (d/'plans.hex').write_bytes(expected.read_bytes())
        modules=[board/(s+'.sv') for s in ('nes_domain_reset124','nes_native_mailbox206','nes_plan_batch206','nes_plan_spi200')]
        execute('vlib',['work'],'lib')
        execute('vlog',['-sv',*modules,bench/'plan_credit557_tb.sv',bench/'plan569_tb.sv'],'compile')
        result[name]=dict(modules={m.name:sha(m) for m in modules},phases=[])
        for phase in [0,11000]:
            def sim(top,flags,label=None):
                log=execute('vsim',['-c',top,*flags,'-do','run -all; quit -f'],label or top+str(phase))
                assert '** Fatal:' not in log,(name,phase,log[-900:])
                return log
            spi=sim('plan_credit557_tb',['+PHASE='+str(phase)])
            assert 'PASS BANK557' in spi
            bus=sim('plan569_tb',['+SHIFT'] if phase else [])
            assert 'PASS569 STOP=16 faults=3 reuse=1 retire=1' in bus
            events=[s for s in bus.splitlines() if s.startswith('# EV ')]
            events+= [s for s in spi.splitlines() if s.startswith(('# CHECK ','# WRITABLE ','# PASS BANK557'))]
            if name=='reference':reference[phase]=events
            else:assert reference[phase]==events,(name,phase)
            trace=d/f'events{phase}.txt';trace.write_text('\n'.join(events)+'\n')
            # Repeat the real 954 E8/E9 arrival and tile-completion schedule
            # from the same run used for the 53-screen replay.
            idx=1 if phase==0 else 2
            count=fixture(args.traces/f'nes-owner562-run{idx}',args.plans,d)
            for early in (0,1):
                timed=sim('plan_credit557_tb',['+TIMED','+PHASE='+str(phase),'+EARLY='+str(early)],f'timed{idx}-{early}')
                assert f'E8={count} plans=23' in timed and 'PASS TIMED557' in timed
            first=[s.split() for s in events if s.startswith('# EV 0 ')]
            stamps={k:[int(r[4]) for r in first if r[3]==k] for k in ('SEND','CAP','WAIT','ACK')}
            # The next host SEND and mailbox CAP can precede the decoder WAIT.
            # Each decoder consumes its word before releasing its corresponding host copy.
            assert all(len(x)==3 for x in stamps.values())
            for i in range(3):
                assert stamps['SEND'][i]<stamps['CAP'][i]<stamps['WAIT'][i]<stamps['ACK'][i]
                if i:assert stamps['ACK'][i-1]<stamps['SEND'][i]
            result[name]['phases'].append(dict(phase_ps=phase,events=len(events),trace=sha(trace),stamps_ps=stamps,E8=count,E9=3,spi=sha(d/'spi.dat'),done=sha(d/'done.dat')))
        if name=='direct':
            # Releasing the host word on entry would return the first bank
            # while it still has unread plans. The bank reservation must fail.
            src=(board/'nes_plan_batch206.sv').read_text()
            mutant=d/'early_credit.sv'
            mutant.write_text(once(src,'state==CHECK&&shape_ok&&lease_ok&&remaining==1;','state==WAIT&&word_valid;'))
            execute('vlog',['-sv',mutant],'mutant-build')
            log=execute('vsim',['-c','plan569_tb','-do','run -all; quit -f'],'early-credit')
            assert '** Fatal: early bank reservation release' in log and 'PASS569' not in log
            result['early_credit_rejected']=True
    (args.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','board','bin','out','fixtures','traces','plans'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
