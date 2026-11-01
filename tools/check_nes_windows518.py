# SPDX-License-Identifier: MIT
"""Exercise boundary ticks and the exact post-STOP report on the linked STM32 image."""
import argparse
import json
from pathlib import Path
from check_nes_game478 import Machine, sha
from nes_windows518 import duration_ms, windows

def run(a):
    m=Machine(a.arm,bytes(128))
    m.call('nes_budget210_reset',[])
    base=0x20012000
    def report():
        n=m.call('nes_budget210_format',[base,6144])
        assert 0<n<6144 and m.u.mem_read(base+n,1)==b'\0'
        return bytes(m.u.mem_read(base,n)).decode('ascii')
    assert [w['displays'] for w in windows(report(),60000)]==[0,0]
    ticks=[0,99,100,3999,4000,5999,6000,6011]
    before=0
    for tick in ticks:
        m.call('nes_budget210_frame',[before])
        m.call('nes_budget210_display',[tick,m.video]);before=tick
    m.call('nes_budget210_frame',[6012]) # unfinished frame
    out=report();result=windows(out,60070)
    assert [w['displays'] for w in result]==[2,2]
    assert result[0]['fps']==2/39 and result[1]['fps']==2/20
    # The old per-frame-start bins and the new completion windows use different boundaries.
    assert sum(int(line.split('=')[1].split(',')[0],16) for line in out.splitlines()
               if line.startswith('b') and len(line)>4 and line[1:3].isdigit() and line[3]=='=')==len(ticks)
    assert 'open=1\n' in out and m.call('nes_budget210_format',[base,32])==0xffffffff
    m.call('nes_budget210_reset',[])
    assert all(w['displays']==0 for w in windows(report(),60000))
    assert windows('bin_ticks=500\n',60000) is None
    for invalid,time in [(out,59990),(out.replace('display_1_40_60=2,2','display_1_40_60=2,-1'),60000)]:
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
                accepted=result,reset=True,unfinished_excluded=True,legacy_bins_preserved=True,legacy_window_result=None)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=run(a);a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(r)
