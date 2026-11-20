"""Check six manifest words per loop; empty requirements impose no WRAM bits."""
import hashlib
import json
from pathlib import Path
from boot_nes_column854 import build
from build_nes_trace_replay import Code

ORIGIN=0x7e2000
PROBES=Path(__file__).resolve().parents[2]/'probes'
BASE=PROBES/'nes-packed883-shared'
WORK=PROBES/'nes-coverage886'

def replacement():
    client=BASE/'client02'
    labels=json.loads((client/'labels.json').read_bytes())
    old=(client/'body.bin').read_bytes()
    assert hashlib.sha256(old).hexdigest()=='d7e31c1f528b7381edf21ea0beaf9585c488fa7b52dde0761a202afc9c9a4910'
    start,end=labels['coverage_loop212'],labels['missing619']
    c=Code(start)
    c.labels.update(labels)
    # For each required bit, the bank's independent receipt must contain it.
    # (~required | valid) + 1 is zero in 16-bit mode exactly on coverage.
    for off in range(0,12,2):
        c.long(0xbf,0x400028+off)
        c.branch(0xf0,f'next{off}')
        c.emit(0x49,0xff,0xff)
        c.absolute(0x19,0x1320+off)
        c.emit(0x1a)
        c.branch(0xd0,'missing619')
        c.label(f'next{off}')
    c.emit(0x98,0x18,0x69,12,0,0xa8,0x8a,0x18,0x69,12,0,0xaa,0xe0,144,0)
    c.branch(0xd0,'coverage_loop212')
    c.branch(0x80,'covered619')
    code=c.finish()
    assert len(code)<=end-start
    return old, labels, start-ORIGIN,code.ljust(end-start,b'\xea')


def prepare():
    old,labels,pos,code=replacement()
    out=WORK/'client02'
    build(BASE/'client02',out,old[:pos]+code+old[pos+len(code):],labels)
    meta=json.loads((out/'build.json').read_bytes())
    meta.update(candidate='coverage886',new_WRAM_B=0)
    (out/'build.json').write_text(json.dumps(meta,indent=2)+'\n')


if __name__=='__main__':
    prepare()
