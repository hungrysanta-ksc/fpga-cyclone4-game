"""Compare a sealed one-descriptor upload in the remaining NTSC blank."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_chr951
import nes_window924
from boot_nes_column854 import build
from build_nes_trace_replay import Code
from nes_native_local165 import call
from nes_ready958 import WORK, complete_row_set, feedback, replay, supply
from nes_receipt941 import BASE as LOADER_SOURCE
from prepare_nes_trial950 import ROM

ORIGIN = 0x7e2000
OUT = ROM.parents[1] / 'nes-blank959' / 'early'


def edits(retry=False):
    labels = json.loads((ROM/'labels.json').read_bytes())
    body = (ROM/'body.bin').read_bytes()
    if retry == 'ordered':
        # Count the checked group first, then sample the beam once. Both
        # success paths keep the original DMA and its normal STOP service.
        first = labels['group538'] - ORIGIN
        fresh = labels['fresh618'] - ORIGIN
        group = labels['group_ready538'] - ORIGIN
        prep = labels['prepare665'] - ORIGIN
        wait = (labels['group_wait912'] & 65535).to_bytes(2,'little')
        assert body[first:first+11] == bytes.fromhex('ae5212ec501290034c1a2c')
        assert body[fresh:fresh+6] == bytes.fromhex('ae5212a96010')
        assert body[group+3:group+8] == bytes.fromhex('20682d9070')
        site = body.index(b'\xae\x52\x12\x20'+wait, prep, prep+32) + 3
        def jump(offset):
            return b'\x4c' + ((ORIGIN+offset)&65535).to_bytes(2,'little')
        branch = (fresh+3)-(first+8)
        assert 0 < branch < 128
        replacements = [(first+7, bytes([branch])), (site, jump(first+11)),
                        (fresh, jump(group+3)), (group+4, wait)]
        result = edits()
        for pos, data in replacements:
            result.extend((pos+i,body[pos+i],v) for i,v in enumerate(data) if body[pos+i]!=v)
        return result
    if retry:
        start = labels['group_wait912']
        end = labels['select920']
        c = Code(start)
        c.labels.update(labels)
        c.emit(0xe2,0x20)
        c.absolute(0xad,0x1024)
        c.branch(0xf0,'fresh8')
        call(c,'beam935')
        c.branch(0xb0,'fresh8')
        c.emit(0xc9,241)
        c.branch(0xb0,'fresh8')
        c.emit(0xc9,230,0xc2,0x20)
        c.branch(0xb0,'one')
        c.absolute(0xad,0x1256)
        c.emit(0xc9,0,6)
        c.branch(0xb0,'permit')  # Existing small-group allowance through line 229.
        c.label('one')
        c.long(0xbf,0x7e4002)
        c.emit(0x29,0,0x30,0xc9,0,0x20)
        c.branch(0xd0,'fresh')
        c.long(0xbf,0x7e4004)
        c.emit(0xc9,0x81,7)
        c.branch(0xb0,'fresh')
        c.emit(0x8a,0x18,0x69,8,0)
        c.absolute(0x8d,0x103a)  # Immutable group's exclusive end.
        c.label('permit')
        c.emit(0xe2,0x20)
        c.absolute(0xad,0x4212)
        c.branch(0x10,'fresh8')
        c.emit(0xc2,0x20)
        call(c,'service')
        c.branch(0xf0,'ok')
        c.jump('cancel169')
        c.label('ok')
        c.emit(0x38,0x60)
        c.label('fresh8')
        c.emit(0xc2,0x20)
        c.label('fresh')
        c.jump('wait169')
        data = c.finish()
        assert len(data)<=end-start, (len(data),end-start)
        pos = start-ORIGIN
        return [(pos+i,body[pos+i],v) for i,v in enumerate(data) if v!=body[pos+i]]
    start = labels['group538'] - ORIGIN
    end = labels['fresh8_618'] - ORIGIN
    gate = body[start:end]
    cap = bytes.fromhex('bf 04 40 7e c9 81 01 b0')
    line = bytes.fromhex('c9 e1 90 1f c9 fd b0')
    assert gate.count(cap) == gate.count(line) == 1
    # Change only the limits in the existing check of a single, checked,
    # non-raw VRAM descriptor. It checks beam, STOP and blank again.
    return [(start+gate.index(cap)+6, 1, 7), (start+gate.index(line)+5, 253, 241)]


def prepare(retry):
    out = OUT.with_name(str(retry)) if retry else OUT
    labels = json.loads((ROM/'labels.json').read_bytes())
    body = bytearray((ROM/'body.bin').read_bytes())
    for offset, old, new in edits(retry):
        assert body[offset] == old
        body[offset] = new
    if not out.exists():
        build(LOADER_SOURCE, out, bytes(body), labels, compact_mvn=True, minimum=2)
    assert (out/'body.bin').read_bytes() == body
    print((out/'build.json').read_text()[-300:])


def run(temp, phase, mode, retry):
    tag = '959' + (retry or '') + mode
    if mode in ('credit','closed'):
        assert retry=='ordered'
        with patch.object(nes_chr951,'ROM',OUT.with_name('ordered')):
            feedback(temp,phase,close=mode=='closed',trial_tag=tag,
                     baseline_tag='959orderedstatic',credit_tag='959orderedcredit')
        return
    if mode == 'static':
        with patch.object(nes_chr951, 'ROM', OUT.with_name(retry) if retry else OUT), complete_row_set():
            replay(temp, phase, 'cold', 'banked', wrap=lambda base:supply(base,'checked'),
                   tag=tag, work_arm=WORK, edition=955)
        return
    # After this SEAL the 906 reply corrections have already taken place.
    # Isolate just its effect, with identical earlier ARM, PPU and SPI phases.
    original = nes_window924.trace
    def monitor(source, scene):
        script = original(source, scene)
        mark = 'packet=requests[index];sample516("load");'
        assert script.count(mark) == 1
        writes = []
        for offset, old, new in edits(retry):
            addr = ORIGIN + offset - 0x7e0000
            writes.append(f'assert(rd({addr})=={old});emu.write({addr},{new},emu.memType.snesWorkRam)')
        hook = 'if pw(8)==906 and pb(0)==3 then ' + ';'.join(writes) + ' end;'
        return script.replace(mark, mark+hook)
    with patch.object(nes_window924, 'trace', monitor):
        feedback(temp, phase, close=True, trial_tag=tag)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare','seal','static','credit','closed'))
    parser.add_argument('temp', type=Path)
    parser.add_argument('phase', nargs='?', type=int, choices=(1,2))
    parser.add_argument('--retry',nargs='?',const='retry',choices=('ordered','retry'))
    args = parser.parse_args()
    if args.mode == 'prepare':
        prepare(args.retry)
    else:
        run(args.temp, args.phase, args.mode,args.retry)
