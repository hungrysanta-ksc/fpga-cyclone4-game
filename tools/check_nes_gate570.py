# SPDX-License-Identifier: MIT
"""Exercise the clock guard and production direct join, including an E9 already on the wire."""
import argparse
import json
import re
from pathlib import Path
import subprocess
from nes_raw506 import once,sha
from replay_nes_banks557_rtl import fixture


def run(a):
    root=Path(__file__).resolve().parents[1];bench=root/'tests/nes-functional'
    a.out.mkdir(parents=True,exist_ok=False)
    result={}
    pins=json.loads((root/'analysis/end557-verification.json').read_text())['directed_RTL']
    targets=[('shared',a.shared_bulk)] if a.shared_bulk else [('base',a.base),('transport',a.transport),('joint',a.board)]
    if a.local_release:targets=[('local',a.local_release)]
    for name,board in targets:
        d=a.out/name;d.mkdir()
        def execute(exe,argv,label):
            p=d/(label+'.log')
            with p.open('wb') as f:
                subprocess.run([str(a.bin/(exe+'.exe')),*map(str,argv)],cwd=d,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=120)
            return p.read_text(errors='replace')
        def sim(top,flags,label,marker):
            log=execute('vsim',['-c',top,*flags,'-do','run -all; quit -f'],label)
            assert marker in log and '** Fatal:' not in log,(label,log[-700:])
            return log
        modules=('domain_reset124','diag_clock_guard127','diag_startup_guard','rom_physical','native_mailbox206','native_arbiter165',
                 'plan_spi200','plan_batch206','tile205','chr_cache192','source_tile192','bulk_aperture188','bulk_control194','tile_bulk206','direct206')
        files=[board/('nes_'+n+'.sv') for n in modules]
        (d/'requests.hex').write_text(''.join(f'{v:02x}\n' for r in pins['requests'] for v in bytes.fromhex(r)))
        expect=a.fixtures/'plans.hex';assert sha(expect)=='3c501203ace52bede32dbca9ed043835cc7a6444a66d8fbd3846da1f3f180f8d'
        (d/'plans.hex').write_bytes(expect.read_bytes())
        guard=(bench/'guard563_tb.sv').read_text()
        guard=once(guard,'mem_on=0;ref_on=0;locked=0;','''mem_on=0;ref_on=0;#5000000;
   if(guard_fault||oe||release_memory)$fatal(1,"no detector clock");
   $display("BOTH570 active_read_no_edges");locked=0;''')
        (d/'guard.sv').write_text(guard)
        bank=(bench/'plan569_tb.sv').read_text()
        timed=(bench/'plan_credit557_tb.sv').read_text()
        if name!='base':
            host_stop='wire host_stop; nes_domain_reset124 parent_stop(host_clk,reset||stop,host_stop);'
            bank=once(bank,' nes_plan_batch206 dut(',host_stop+'\n nes_plan_batch206 dut(.stop(host_stop),')
            timed=once(timed,' nes_plan_batch206 transport(', ' wire host_stop; nes_domain_reset124 parent_stop(hc,reset,host_stop);\n nes_plan_batch206 transport(')
            timed=once(timed,'.nes_clk(nc),.reset(reset),.stop(1\'b0)', '.nes_clk(nc),.reset(reset),.stop(host_stop)')
        if name=='local':
            bank=once(bank,'dut(.stop(host_stop),',"dut(.reset(1'b0),.stop(host_stop),")
            timed=once(timed,'.nes_clk(nc),.reset(reset),.stop(host_stop)',".nes_clk(nc),.reset(1'b0),.stop(host_stop)")
        (d/'banks.sv').write_text(bank);(d/'timed.sv').write_text(timed)
        execute('vlib',['work'],'lib')
        execute('vlog',['-sv','+define+SPLIT',*files,d/'guard.sv',bench/'gate570_tb.sv',d/'banks.sv',d/'timed.sv'],'compile')
        phases=[]
        for phase in (0,1):
            shift=['+SHIFT'] if phase else []
            log=sim('gate570_tb',shift+(['+GUARDED'] if name!='base' else [])+(['+INGRESS'] if name in ('joint','shared','local') else []),
                    f'top{phase}','PASS570 TOP')
            credits=[int(n) for n in re.findall(r'PRE570 kind=\d writable=(\d)',log)]
            assert credits==([1]*3 if name=='base' else [0]*3)
            trailer=int(re.search(r'TRAILER570 accepted=(\d+)',log)[1])
            g=sim('guard563_tb',shift,f'guard{phase}','PASS563 6 losses')
            assert 'BOTH570 active_read_no_edges' in g
            loss=[list(map(int,r)) for r in re.findall(r'LOSS563 (\d) (\d) (\d+)',g)]
            assert len(loss)==6
            b=sim('plan569_tb',shift,f'banks{phase}','PASS569 STOP=16 faults=3 reuse=1 retire=1')
            count=fixture(a.traces/f'nes-owner562-run{phase+1}',a.plans,d)
            for early in (0,1):
                sim('plan_credit557_tb',['+TIMED',f'+PHASE={phase*11000}',f'+EARLY={early}'],
                    f'spi{phase}-{early}',f'E8={count} plans=23')
            phases.append(dict(credits=credits,accepted_after_fault=trailer,loss_ps=loss,
                starts_ps=[int(n) for n in re.findall(r'START563 (\d+)',g)],E8=count,E9=3,
                bank_events=len(re.findall(r'^# EV',b,re.M))))
        result[name]=dict(phases=phases,modules={f.name:sha(f) for f in files})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','transport','board','bin','out','fixtures','traces','plans'):p.add_argument('--'+k,type=Path,required=True)
    group=p.add_mutually_exclusive_group()
    group.add_argument('--shared-bulk',type=Path);group.add_argument('--local-release',type=Path)
    run(p.parse_args())
