# SPDX-License-Identifier: MIT
"""492 parser regression using explicitly relabelled489 fixtures, not492 hardware."""
import argparse,json,re,shutil
from pathlib import Path
from analyze_nes_supply485_hardware import analyse
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['raw489','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(exist_ok=False);fixture=a.out/'fixture';fixture.mkdir()
    for k in ['progress','budget','game-last']:
        name=f'nes-{k}-mmc489.txt';s=(a.raw489/name).read_text(encoding='utf-8-sig')
        (fixture/name.replace('489','492')).write_text(s.replace('MMC489','MMC492'),encoding='utf8')
    real=analyse(a.raw489,489);mock=analyse(fixture,492)
    assert mock['display']==real['display'] and mock['DWT_phases_nested']==real['DWT_phases_nested']
    negatives=[]
    for key,value in [('native_result','5'),('native_video_error','15'),('native_receiver_error','2'),
                      ('native_sink_error','2'),('sink_window_error','2'),('plan_error','0'),
                      ('plan_end','1'),('plan_sent','1'),('trace_aborts','1'),('native_frames','578'),
                      ('fault_context_valid','1'),('load_result','2')]:
        d=a.out/key;d.mkdir()
        for q in fixture.glob('*.txt'):shutil.copyfile(q,d/q.name)
        q=d/'nes-game-last-mmc492.txt';s=q.read_text();s,n=re.subn(rf'(?m)^{key}=.*$',f'{key}={value}',s);assert n==1;q.write_text(s)
        try:analyse(d,492)
        except AssertionError:negatives.append(key)
        else:raise AssertionError('Unexpected failure accepted:'+key)
    r={'passed':True,'scope':__doc__,'fixture_label_only_not_new_hardware':True,'negative_cases':negatives,
       'baseline489_read_unchanged':True,'whole_elapsed_and_phase_counters_equal_under_label_change':True}
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'negatives':len(negatives),'actual492_data':False}))
