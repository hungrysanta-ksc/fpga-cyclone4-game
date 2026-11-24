"""Prepare the MMC966 diagnostic link with a single same-generation SPI read."""
import shutil
import hashlib
import json
from pathlib import Path

from nes_display1010 import once, ROOT

PROBE = ROOT.parent/'probes/nes-display1010/link'


def prepare():
    source = ROOT.parent/'probes/nes-trial966/link'
    baseline=json.loads((ROOT/'analysis/trial966-package.json').read_bytes())
    if hashlib.sha256((source/'src/obj-nes-100/firmware.stm').read_bytes()).hexdigest()!=baseline['firmware']:
        raise ValueError('different reference firmware')
    shutil.copytree(source, PROBE, ignore=shutil.ignore_patterns('*.log'))
    src = PROBE/'src'
    header = src/'nes_frame900.h'
    s = once(header.read_text(), 'wire[16]', 'wire[32]')
    s = once(s, '==44', '==60')
    a = s.index('uint16_t selected,score')
    b = s.index(';};', a)
    header.write_text(s[:a]+'uint16_t displayed55'+s[b:], newline='\n')
    budget = src/'nes_budget210.c'
    s = once(budget.read_text(), 'page905(h,256) && h[1]==0x95',
             'page905(h,0) && h[1]==0xa1 && h[30]==15 && h[31]==0xa5')
    a, b = s.index(' uint8_t page[32]'), s.index('trace_done:\n')
    s = s[:a]+''' if(mode900!=3 && native_runtime165.receiver &&
    native_runtime165.receiver->state==NES_NATIVE165_COMPLETE){
  pending950=r;start950=t;return;
 }
 if(mode900!=3 && header950(r))r->valid|=4;
'''+s[b+len('trace_done:\n'):]
    budget.write_text(once(s, 'edition=966','edition=1010'), newline='\n')
    for name in ('nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION'):
        f=src/name
        f.write_bytes(f.read_bytes().replace(b'966',b'1010'))


if __name__=='__main__':
    prepare()
