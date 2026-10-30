# SPDX-License-Identifier: MIT
"""492/493 parser regression using relabelled489 fixtures, not new hardware."""
import argparse,json,re,shutil
from pathlib import Path
from analyze_nes_supply485_hardware import analyse
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['raw489','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--trial',type=int,choices=[492,493],default=492)
    a=p.parse_args();a.out.mkdir(exist_ok=False);fixture=a.out/'fixture';fixture.mkdir()
    for k in ['progress','budget','game-last']:
        name=f'nes-{k}-mmc489.txt';s=(a.raw489/name).read_text(encoding='utf-8-sig')
        (fixture/name.replace('489',str(a.trial))).write_text(s.replace('MMC489',f'MMC{a.trial}'),encoding='utf8')
    real=analyse(a.raw489,489);mock=analyse(fixture,a.trial)
    assert mock['display']==real['display'] and mock['DWT_phases_nested']==real['DWT_phases_nested']
    negatives=[]
    for key,value in [('native_result','5'),('native_video_error','15'),('native_receiver_error','2'),
                      ('native_sink_error','2'),('sink_window_error','2'),('plan_error','0'),
                      ('plan_end','1'),('plan_sent','1'),('trace_aborts','1'),('native_frames','578'),
                      ('fault_context_valid','1'),('load_result','2')]:
        d=a.out/key;d.mkdir()
        for q in fixture.glob('*.txt'):shutil.copyfile(q,d/q.name)
        q=d/f'nes-game-last-mmc{a.trial}.txt';s=q.read_text();s,n=re.subn(rf'(?m)^{key}=.*$',f'{key}={value}',s);assert n==1;q.write_text(s)
        try:analyse(d,a.trial)
        except AssertionError:negatives.append(key)
        else:raise AssertionError('Unexpected failure accepted:'+key)
    r={'passed':True,'scope':__doc__,'fixture_label_only_not_new_hardware':True,'negative_cases':negatives,
       'baseline489_read_unchanged':True,'whole_elapsed_and_phase_counters_equal_under_label_change':True}
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'negatives':len(negatives),'fixture_trial':a.trial,'actual_trial_data':False}))
