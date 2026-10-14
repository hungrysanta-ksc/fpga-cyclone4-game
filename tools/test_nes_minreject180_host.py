# SPDX-License-Identifier: MIT
"""Actual C schema3 reader, old versions rejected, decoder visibility contract."""
import inspect,json
from pathlib import Path
import test_nes_reject180_host as prior
from decode_nes_minreject180 import record,decode
from nes_game147 import ROOT,sha

source=inspect.getsource(prior.main)
source=source.replace('rx[7]=2;', 'rx[7]=3;').replace('case 14:rx[2]=rx[3]=rx[4]=0;break;', 'case 14:rx[2]=rx[3]=rx[4]=0;break;case 15:rx[7]=2;break;')
source=source.replace('mode<15','mode<16').replace('mode==0||mode>=13','mode==0||mode==13||mode==14')
source=source[:source.index('    # Independent literal vector')]+'''
    fields=[(1,2),(255,8),(0x1888242,25),(511,9),(511,9),(24,8),(224,8),(32,6),(128,8),(128,8),(31,5)]
    v=0
    for x,bits in fields:v=(v<<bits)|x
    raw=f'{v:024x}';r=record(raw)
    assert [r[n] for n in ['kind','generation_mod256','errors','candidate_display_mask','rows','groups','objects','exceptions','palettes_saturated31']]==[1,255,0x1888242,24,224,32,128,128,31]
    assert not r['position_observed'] and 'first_line' not in r and 'first_mask' not in r
    assert (r['rom_fault'],r['raster_errors'],r['compact_errors'],r['fetch_errors'])==(True,0x88,0x82,0x42)
    text='ppu_history_kind=LAST16_EPISODE180_V3\\nppu_history_valid=1\\nppu_history_count=1\\nppu_history_flags=1\\nppu_history_00='+raw+'\\n'
    assert len(decode(text)['events'])==1
    for bad in [text.replace('LAST16_EPISODE180_V3','LAST16_REJECT180_V2'),text.replace('valid=1','valid=0'),text.replace('_00=','_01=')]:
        try:decode(bad)
        except AssertionError:pass
        else:raise AssertionError('invalid decoder input accepted')
    try:record(f'{v ^ (1<<52):024x}')
    except AssertionError:pass
    else:raise AssertionError('measured position accepted under schema3')
    result=dict(passed=True,reader_cases=16,decoder_vectors=5,source_sha256=sha(a.arm/'src/nes_run136.inc'),generated_sha256=sha(f),public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_minreject180_host.py','tools/test_nes_reject180_host.py','tools/decode_nes_minreject180.py','tools/decode_nes_reject180.py']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\\n');print('PASS MINREJECT180 C16/decoder5')
'''
ns=dict(prior.__dict__);ns.update(record=record,decode=decode)
exec(compile(source,'minreject180_host','exec'),ns)
if __name__=='__main__':ns['main']()
