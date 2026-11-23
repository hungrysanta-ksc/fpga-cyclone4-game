"""Schedule checked final-credit polls after the next input has reached END."""
import argparse
import shutil
from pathlib import Path
from unittest.mock import patch

import nes_oam944 as base
from nes_raw506 import once, sha

MODES = ('complete', 'paced', 'quiet', 'skip', 'prepared_index', 'sealed_index', 'receipt', 'receipt_fit', 'warm_begin', 'warm_header')
ROOT = base.ROOT.parent / 'nes-handoff945'


def work(mode):
    return ROOT / mode


def index_path(link, mode):
    c = link/'src/nes_resident211.c'
    h = link/'src/nes_resident211.h'
    runtime = link/'src/nes_native_runtime165.c'
    source = c.read_text()
    if mode == 'prepared_index':
        # A second BEGIN requires a successful prepare and commit of its predecessor.
        # A reset/epoch change empties both slot tables, including epoch zero.
        source = once(source, ' rebuild221(s);\n return true;',
                      ' if(!s->bg_slots && !s->obj_slots)memset(s->index_head,255,sizeof s->index_head);\n return true;')
        source = once(source, 's->prepared=true;return true;', 'rebuild221(s);s->prepared=true;return true;')
    else:
        # Use existing structure padding. Rebuild only scratch collision chains.
        # Other callers can enter BEGIN without a runtime SEAL callback.
        header = once(h.read_text(), 'uint8_t first_bg_rows;', 'uint8_t first_bg_rows; bool index_prebuilt;')
        h.write_text(once(header, 'void nes_resident211_reset(', 'void nes_resident945_preindex(struct nes_resident211 *);\nvoid nes_resident211_reset('), newline='\n')
        source = once(source, 'static unsigned find221(', '''void nes_resident945_preindex(struct nes_resident211 *s){
 if(s && s->prepared && !s->fault && !s->index_prebuilt){rebuild221(s);s->index_prebuilt=true;}
}
static unsigned find221(''')
        source = once(source, 's->epoch=epoch;', 's->epoch=epoch;s->index_prebuilt=false;')
        source = once(source, ' rebuild221(s);\n return true;', ' if(!s->index_prebuilt)rebuild221(s);\n s->index_prebuilt=false;return true;')
        code = once(runtime.read_text(), 'if(reason==3){s->prefetch_left=17;', 'if(reason==3){nes_resident945_preindex(s->resident);s->prefetch_left=17;')
        runtime.write_text(code, newline='\n')
    c.write_text(source, newline='\n')


def prepare(mode):
    source = base.work('smallbg') / 'link'
    assert sha(source / 'src/obj-nes-100/firmware.stm') == 'e14995c9f0617debbd8aa2c124a41d0422908af9b2f01f220e56bbe30f0f0f93'
    link = work(mode) / 'link'
    shutil.copytree(source, link)
    if mode in ('receipt','receipt_fit','warm_begin','warm_header'):
        path = link/'src/nes_sink_window184.c'
        # SEAL is a synchronous barrier. Its complete identity has already been checked.
        # send() rechecks the guard; BEGIN retains its own full post-send receipt.
        code = once(path.read_text(), '(p[0]!=3 || s->last[1]!=5) && !nes_window184_drain',
                    '(p[0]==1 ? (s->last[0]!=3 || s->sent!=s->retired) : (p[0]!=3 || s->last[1]!=5)) && !nes_window184_drain')
        if mode in ('receipt_fit','warm_begin','warm_header'):
            # Only barrier() can submit SEAL. Its successful return proves full retirement.
            code = once(code, '(s->last[0]!=3 || s->sent!=s->retired)', 's->last[0]!=3')
        if mode in ('warm_begin','warm_header'):
            anchor=' if(s->ever_sent && (p[0]==1 ?'
            code = once(code, anchor, ' uint32_t serial;memcpy(&serial,s->last+4,sizeof serial);\n'+anchor)
            code = once(code, 'p[0]==1 ? s->last[0]!=3', 'p[0]==1 ? (s->last[0]!=3 || serial<2)')
        if mode == 'warm_header':
            # The window starts zeroed; both sending APIs exclude opcode zero.
            # Keep writing ever_sent for ABI compatibility but use the saved opcode for reads.
            code = once(code, 'if(!s->ever_sent)', 'if(!s->last[0])')
            code = once(code, 's->ever_sent&&!receipt_matches', 's->last[0]&&!receipt_matches')
            code = once(code, 's->ever_sent && s->last[0]==3', 's->last[0]==3')
            code = once(code, 'if(s->ever_sent && (p[0]==1', 'if(s->last[0] && (p[0]==1')
        path.write_text(code, newline='\n')
        return
    if mode.endswith('_index'):
        index_path(link, mode)
        return
    path = link / 'src/nes_native_runtime165.c'
    code = path.read_text()
    if mode == 'skip':
        # With END checked, consumed() and the empty receive loop cannot advance input.
        code = once(code, 's->prefetch_left && (input_wait || reason==2)',
                    's->prefetch_left && (input_wait || (reason==2 && r->state!=NES_NATIVE165_COMPLETE))')
    elif mode == 'quiet':
        # Reuse the normal quiet interval for a complete receiver. Idle still polls immediately.
        code = once(code, 'reason==2 && (r->state==NES_NATIVE165_COMPLETE || r->state==NES_NATIVE165_IDLE) ? 0',
                    'reason==2 && r->state==NES_NATIVE165_IDLE ? 0')
    else:
        # There is no further input block to receive before the previous identity retires.
        cycles = '0' if mode == 'complete' else '84u*96u'
        anchor = ' if(reason==1 && progress && r->state==NES_NATIVE165_IDLE'
        code = once(code, anchor, ' if(reason==2 && r->state==NES_NATIVE165_COMPLETE)\n'
                    f'  return nes_cost474_pause(ctx,check,2,progress,{cycles});\n' + anchor)
        code = once(code, 'reason==2 && (r->state==NES_NATIVE165_COMPLETE || r->state==NES_NATIVE165_IDLE) ? 0',
                    'reason==2 && r->state==NES_NATIVE165_IDLE ? 0')
    path.write_text(code, newline='\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'replay', 'proof', 'guards'))
    p.add_argument('mode', choices=MODES)
    p.add_argument('temp', type=Path)
    p.add_argument('phase', nargs='?', type=int, choices=(1, 2))
    p.add_argument('cache', nargs='?', choices=('warm', 'cold'))
    a = p.parse_args()
    arm = work(a.mode)
    tag = '945' + a.mode
    if a.action == 'prepare':
        prepare(a.mode)
    elif a.action == 'replay':
        with patch.object(base.prev.chain, 'output', lambda _: base.prev.prior.ROM):
            base.prev.chain.replay(a.temp, 'final', a.phase, a.cache, 'bounded', work_arm=arm, tag=tag)
    elif a.action == 'proof':
        from check_nes_supply905_arm import run
        from nes_order938 import empty_next_offer
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes', arm, 925,
            short_header=True, order=empty_next_offer, marker_values=(4,8,16,24))
    else:
        import check_nes_discovery942 as checks
        with patch.object(checks, 'work', work):
            checks.check(a.temp, a.mode, tag=tag, record='safety945.json')
