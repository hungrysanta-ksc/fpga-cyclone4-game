# SPDX-License-Identifier: MIT
"""Paired candidate: uniform NES left clipping, explicit20-byte SEAL, SNES window.

Accept only1e (unclipped) or18 (BG+OBJ left8 clipped). Other rendering modes
and within-frame changes remain rejected. No memory/capacity/timeout increase.
Not selected for hardware until functional, link, fit and packaging checks pass.
"""
from pathlib import Path
import argparse, inspect, json
import nes_boot172 as boot
import nes_banked169 as banked


def replace(s, old, new):
    assert s.count(old) == 1, old
    return s.replace(old, new)


def raster(s):
    return replace(s, "if(display_mask!=8'h1e)errors[6]<=1;", """//178: uniform left8 clipping is represented by the final SNES window.
    // Keep blank/emphasis/grayscale and within-frame mask changes rejected.
    if((display_mask!=8'h1e && display_mask!=8'h18) ||
       (!begin_packet && display_mask!=line_mask))errors[6]<=1;""")


def header(s):
    # Occupies the existing byte of alignment padding before the uint16 arrays.
    return replace(s, ' uint16_t hofs[224],vofs[224];',
                   ' uint8_t display_mask; /*178: uniform1e or18, no extra frame buffer. */\n uint16_t hofs[224],vofs[224];')


def converter(s):
    s = replace(s, ' unsigned palettes=s->counts[5]/32;', ''' unsigned palettes=s->counts[5]/32;
 p->display_mask=(uint8_t)(s->raster[0]>>36);
 if(p->display_mask!=0x1e && p->display_mask!=0x18)return fail(p,3);''')
    return replace(s, '((s->raster[y]>>36)&255)!=0x1e',
                   '((s->raster[y]>>36)&255)!=p->display_mask')


def sink(s):
    s = replace(s, ' const uint8_t *data[4]=',
                ' if(p->display_mask!=0x1e && p->display_mask!=0x18)return fail(s,5);\n const uint8_t *data[4]=')
    s = replace(s, ' uint8_t descriptor[18];', ' uint8_t descriptor[20];')
    s = replace(s, ' if(!packet(s,3,0,0,descriptor,18))return false;', ''' put16(descriptor+18,p->display_mask);
 if(!packet(s,3,0,0,descriptor,20))return false;''')
    return s


def emit_upload(c, prefix='upload165'):
    source = inspect.getsource(banked.emit_upload)
    source = replace(source, 'source=inspect.getsource(old.emit_upload)', '''source=inspect.getsource(old.emit_upload)
    source=source.replace("label('scroll')", "label('scroll');c.absolute(0xad,0x123a);c.emit(0xc9,0x18);cond(0xd0,'unclipped178');c.store(0x212e,0x11);jump('window_done178');label('unclipped178');c.store(0x212e,0);label('window_done178')")''')
    namespace = dict(banked.__dict__)
    exec(compile(source, 'clip178-upload', 'exec'), namespace)
    return namespace['emit_upload'](c, prefix)


def client_source(s):
    s = replace(s, ' for a in range(0x2123,0x212c):c.store(a,0)', ''' for a in range(0x2123,0x212c):c.store(a,0)
 # Window1 hides BG1/OBJ at x0..7 only when the committed mask enables it.
 for a,v in [(0x2123,2),(0x2125,2),(0x2126,0),(0x2127,7)]:c.store(a,v)''')
    s = replace(s, 'checkimm(0x120c,18)', 'checkimm(0x120c,20)')
    s = replace(s, " call(c,'local165_entry');lda(0x1236)", ''' c.long(0xaf,0x400022);c.emit(0xc9,0x18,0);cond(0xf0,'mask_valid178');c.emit(0xc9,0x1e,0);cond(0xd0,'bad_packet')
 c.label('mask_valid178');sta(0x123a)
 call(c,'local165_entry');lda(0x1236)''')
    return s


def build(out):
    source = inspect.getsource(boot.build)
    source = replace(source, 'source=Path(original.__file__).read_text()',
                     'source=client_source(Path(original.__file__).read_text())')
    source = replace(source, 'from nes_banked169 import emit_upload',
                     'from nes_clip178 import emit_upload')
    namespace = dict(boot.__dict__)
    namespace['client_source'] = client_source
    exec(compile(source, 'clip178-client', 'exec'), namespace)
    result = namespace['build'](out)
    result.update(scope=__doc__, seal_bytes=20, mask_address=0x123a,
                  clipping='Final vblank only; window1 x0..7 BG1+OBJ. Candidate mask never changes visible window before commit.')
    (out/'build.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    build(p.parse_args().out)
