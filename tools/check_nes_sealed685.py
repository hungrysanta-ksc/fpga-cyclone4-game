"""Real linked receive, STOP/CRC guards with and without retirement progress."""
import argparse,inspect,json
from pathlib import Path
import check_nes_receive682 as prior
from check_nes_game478 import sha
from nes_raw506 import once

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    # The only changed old expectation is reason2+progress: a sealed output
    # has no further output credit user. Reason0/1 retains the old priority.
    source=inspect.getsource(prior.check)
    source=once(source,"if case in ('normal','wrap'):","if case in ('normal','wrap') or (case=='output_progress' and reason==2):")
    ns=dict(vars(prior));exec(source,ns);check=ns['check']
    cases=[check(a.arm,c,r,True,True) for r in (0,1,2,4) for c in
        ('normal','wrap','empty','complete','STOP_before','STOP_after_READ','bad_CRC','bad_retire','failed_IO')]
    cases += [check(a.arm,c,r,True,True) for r in (0,1,2) for c in ('output_progress','zero_credit')]
    cases += [check(a.arm,'plan_busy',r,True,True) for r in (0,1)]
    source=inspect.getsource(prior.burst)
    source=once(source,'def burst(src,case):','def burst(src,case,progress):')
    source=once(source,'[m.rt,m.check|1,2,0]','[m.rt,m.check|1,2,int(progress)]')
    exec(source,ns)
    for progress in (False,True):
        for c in ('cap7','empty_after3','STOP_after3','CRC_third','cache_CRC','cache_token'):
            cases.append(dict(ns['burst'](a.arm,c,progress),retirement_progress=progress))
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=cases,
        scope='Actual ARM callback and CRC/POP, bounded7, unsealed priority, STOP, no input COMMIT/EA or display ACK substitution.'),indent=2)+'\n')
    print('PASS685',len(cases),'linked input/STOP/CRC/credit guards')
