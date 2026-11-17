# SPDX-License-Identifier: MIT
"""Exercise boundary ticks and the exact post-STOP report on the linked STM32 image."""
import argparse
import json
from pathlib import Path
from check_nes_game478 import Machine, sha
from nes_windows518 import DEMO_FIELD, FIELD, TRIMMED_FIELD, LAYOUTS, duration_ms, fps_delta, windows

def run(a):
    m=Machine(a.arm,bytes(128))
    m.call('nes_budget210_reset',[])
    base=0x20012000
    def report():
        n=m.call('nes_budget210_format',[base,6144])
        assert 0<n<6144 and m.u.mem_read(base+n,1)==b'\0'
        return bytes(m.u.mem_read(base,n)).decode('ascii')
    assert [w['displays'] for w in windows(report(),60000)]==[0,0]
    field, ticks = {
        'demo': (DEMO_FIELD,[0,99,100,2999,3000,5999,6000,6011]),
        'trimmed': (TRIMMED_FIELD,[0,99,100,499,500,3999,4000,5499,5500,5999,6000,6011]),
        'legacy': (FIELD,[0,99,100,3999,4000,5999,6000,6011]),
    }[a.layout]
    before=0
    expected=[0,0]
    for tick in ticks:
        m.call('nes_budget210_frame',[before])
        m.call('nes_budget210_display',[tick,m.video]);before=tick
        for i,(start,end) in enumerate(LAYOUTS[field]):
            if start*100 <= tick < end*100:
                expected[i]+=1
        assert [w['displays'] for w in windows(report(),60000)]==expected, tick
    m.call('nes_budget210_frame',[6012]) # unfinished frame
    out=report();result=windows(out,60070)
    assert [w['displays'] for w in result]==[2,2]
    assert tuple((r['start_s'],r['end_s']) for r in result)==LAYOUTS[field]
    assert [r['fps'] for r in result]==[2/(end-start) for start,end in LAYOUTS[field]]
    assert fps_delta(result,result)==[0,0]
    # The old per-frame-start bins and the new completion windows use different boundaries.
    assert sum(int(line.split('=')[1].split(',')[0],16) for line in out.splitlines()
               if line.startswith('b') and len(line)>4 and line[1:3].isdigit() and line[3]=='=')==len(ticks)
    assert 'open=1\n' in out and m.call('nes_budget210_format',[base,32])==0xffffffff
    m.call('nes_budget210_reset',[])
    assert all(w['displays']==0 for w in windows(report(),60000))
    assert windows('bin_ticks=500\n',60000) is None
    other = FIELD if field != FIELD else TRIMMED_FIELD
    try:fps_delta(result, windows(out.replace(field,other),60000))
    except ValueError:pass
    else:raise AssertionError("Compared incompatible windows")
    for invalid,time in [(out,59990),(out.replace(field+'=2,2',field+'=2,-1'),60000),
                         (out+'\n'+other+'=2,2\n',60000)]:
        try:windows(invalid,time)
        except ValueError:continue
        raise AssertionError('Invalid observation accepted')
    progress="MMC518 seq=0 stage=DISPLAY_NEXT elapsed_ms=1234\nMMC518 seq=1 stage=DISPLAY_STOPPED elapsed_ms=61304\nMMC518 seq=2 stage=MENU_PREPARED elapsed_ms=61310"
    assert duration_ms(progress)==60070
    for invalid in (progress.splitlines()[0],progress.replace("seq=1","seq=3"),progress.replace("61310","61000")):
        try:duration_ms(invalid)
        except ValueError:continue
        raise AssertionError("Invalid progress accepted")
    blob=a.arm/'obj-nes-100/firmware.stm'
    return dict(firmware_SHA256=sha(blob),firmware_B=blob.stat().st_size,Flash_free_B=0x34000-blob.stat().st_size,
                BSS_B=int((a.arm.parent/'size.log').read_text().splitlines()[-1].split()[2]),test_ticks=ticks,
                layout=a.layout,accepted=result,reset=True,unfinished_excluded=True,legacy_bins_preserved=True,legacy_window_result=None)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--layout',choices=('legacy','trimmed','demo'),default='legacy')
    a=p.parse_args();r=run(a);a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(r)
