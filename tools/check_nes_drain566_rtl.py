# SPDX-License-Identifier: MIT
"""Replay observed CPU addresses, values and strobe spacing into the fitted 565 RTL sources."""
import argparse
import json
from pathlib import Path
import subprocess
from check_nes_reuse565 import bank_testbench
from nes_raw506 import once,sha


def pulses(rows):
    return '\n'.join(f"pulse566(t+{(r['clock']-rows[0]['clock'])*46562},24'h{r['value']>>8:06x},8'h{r['value']&255:02x});"
                     for r in rows if r['event'].endswith('_write'))


def scenario(case,rows,trace):
    bypass=case.endswith('bypass')
    before=rows[:next((i for i,r in enumerate(rows) if r['event']=='reset_applied'),len(rows))]
    last=next(r for r in before if r['event']=='old_last_read')
    cut=next(r['clock'] for r in before if r['event']=='cancel')-last['clock']
    before=[last]+[r for r in before if r['event'].endswith('_write')]
    n_old=sum(r['event']=='old_write' and r['value']>>8==0x6050 for r in rows)
    src='time t; #120000;reset=0;repeat(20)@(negedge nc);offer566(11);read566(11);t=$time;'
    if bypass:
        src+='reset566();repeat(10)@(negedge hc);reset=0;offer566(31);t=$time;'+pulses(before)
        src+='repeat(12)@(negedge hc);if(returns566!=1||avail||hf565)$fatal(1,"undetected bypass");'
    else:
        src+=f"fork begin {pulses(before)} end begin #{(cut+trace['stop_clock'])*46562};reset566();"
        src+=f"#(t+{(cut+trace['start_clock'])*46562}-$time);reset=0;end join "
        src+=f"offer566(31);if(returns566!={n_old}||hf565)$fatal(1,\"stale consume\");read566(31);t=$time;"
        fresh=rows[next(i for i,r in enumerate(rows) if r['event']=='fresh_last_read'):]
        src+=pulses(fresh)+f'repeat(12)@(negedge hc);if(returns566!={n_old+1}||avail||hf565)$fatal(1,"fresh ACK");'
    return src+'$display("PASS566 returns=%0d",returns566);$finish;'


def main():
    p=argparse.ArgumentParser()
    for k in ('board','bin','phase1','phase2','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    board=a.board.resolve();bench=Path(__file__).resolve().parents[1]/'tests/nes-functional'
    tb=bank_testbench(bench,board)
    start=tb.index(' initial begin\n  #120000;')
    tb=tb[:start]+(bench/'drain566.svh').read_text()+'\n@CASES@\n'+tb[tb.index(' initial begin #1000000000;',start):]
    mods=['domain_reset124','native_mailbox206','bulk_aperture188','bulk_control194','tile205','tile_bulk206']
    inputs=[board/f'nes_{m}.sv' for m in mods]
    result=dict(board_files={f.name:sha(f) for f in [board/'nes_direct206.sv',*inputs]},cases={})
    def run(exe,args,name):
        log=out/(name+'.log')
        with log.open('wb') as f:
            subprocess.run([str(a.bin/(exe+'.exe')),*map(str,args)],cwd=out,stdout=f,stderr=subprocess.STDOUT,
                           check=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
        return log.read_text(errors='replace')
    blocks=[];jobs=[]
    for phase,path in enumerate([a.phase1,a.phase2],1):
        trace=json.loads(path.read_text())
        for case,rows in trace['cases'].items():
            name=f'phase{phase}_{case}'
            blocks.append(f'initial if($test$plusargs("{name}"))begin\n'+scenario(case,rows,trace)+'\nend')
            jobs.append((name,phase))
    src=out/'bank.sv';src.write_text(once(tb,'@CASES@','\n'.join(blocks)))
    run('vlib',['work'],'lib')
    run('vlog',['-sv','+define+EARLY',*inputs,src],'compile')
    for name,phase in jobs:
        log=run('vsim',['-c','close561_tb','+'+name,*(['+SHIFT'] if phase==2 else []),'-do','run -all; quit -f'],name)
        assert 'PASS566 returns=' in log,name
        result['cases'][name]=int(log.split('PASS566 returns=')[1].split()[0])
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    main()
