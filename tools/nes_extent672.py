"""Choose the larger accepted head/tail map in late VBlank; no wait or new credit."""
import argparse,json
from pathlib import Path
from build_nes_trace_replay import Code
from nes_rom636 import build
from nes_raw506 import sha

ORIGIN=0x7e2000

def prepare(base,unpacked,out):
    evidence=json.loads(Path('analysis/entry665-verification.json').read_text())
    assert sha(base/'sink165.sfc')==evidence['client_SHA256']
    body=bytearray((base/'body.bin').read_bytes());labels=json.loads((base/'labels.json').read_text())
    # Only the late233..252 path changes. Earlier tile/head preference, fresh
    # beam checks,1152B cap,STOP/new-head priority and synchronous retire stay.
    start=body.index(bytes.fromhex('bf01407e2970c950'),labels['selected526']-ORIGIN)
    end=labels['map_beam_ok526']-ORIGIN
    assert end-start==49
    c=Code(ORIGIN+len(body));c.labels.update(labels)
    c.label('choose672');c.emit(0xc2,0x20)
    c.long(0xbf,0x7e4000);c.emit(0x29,0,0x70,0xc9,0,0x50);c.branch(0xf0,'old_map672')
    c.emit(0xa0,0,0) # a tile is not eligible after232
    c.label('old_map672');c.emit(0xda);c.absolute(0xad,0x1250);c.emit(0x38,0xe9,8,0,0xaa)
    c.long(0xbf,0x7e4000);c.emit(0x29,0,0x70,0xc9,0,0x50);c.branch(0xd0,'restore672')
    c.emit(0x98);c.long(0xdf,0x7e4004);c.branch(0xb0,'restore672')
    c.long(0xbf,0x7e4004);c.emit(0xc9,0x80,4);c.branch(0x90,'size672');c.emit(0xa9,0x80,4)
    c.label('size672');c.emit(0xa8,0x68,0xe2,0x20);c.jump('map_beam_ok526')
    c.label('restore672');c.emit(0xfa,0xc0,0,0);c.branch(0xf0,'no_map672')
    c.emit(0xe2,0x20);c.jump('map_beam_ok526')
    c.label('no_map672');c.emit(0xe2,0x20);c.jump('defer_beam')
    extra=c.finish();body[start:end]=bytes([0x4c])+struct_word(c.labels['choose672'])+bytes(end-start-3)
    candidate=bytes(body)+extra
    build(unpacked,out,edit_body=lambda old,syms:candidate,allow_extension=True)
    (out/'labels.json').write_text(json.dumps(c.labels,indent=2)+'\n')
    info=json.loads((out/'build.json').read_text());info.update(json.loads((base/'build.json').read_text()))
    packed=json.loads((out/'build.json').read_text())
    for name in ('body_bytes','prefix_B','encoded_B','loader_B','physical_free_B','verify_entry','boot_error'):
        info[name]=packed[name]
    info.update(candidate='extent672',copy_verified_bytes=len(candidate),body_free=5984-len(candidate),
        replacement_range=[start,end],new_control_B=len(extra),old_control_removed_B=end-start,
        late_selection='max accepted head/tail map, old tile/head policy before233',
        independent_validation_unchanged=True)
    (out/'build.json').write_text(json.dumps(info,indent=2)+'\n')
    print(json.dumps({k:info[k] for k in ('body_bytes','physical_free_B','new_control_B','old_control_removed_B')}))

def struct_word(n):return (n&65535).to_bytes(2,'little')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','unpacked','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.base,a.unpacked,a.out)
