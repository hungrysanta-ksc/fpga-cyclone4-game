"""Find an accepted interior map only when the late selected/tail tile cannot run."""
import argparse,json
from pathlib import Path
from build_nes_trace_replay import Code
from prepare_nes_progress680 import client,ORIGIN


def scan(body,labels,*,neighbor=False):
    body=bytearray(body);c=Code(ORIGIN+len(body));c.labels.update(labels)
    c.label('late_map680')
    c.emit(0xc2,0x20);c.absolute(0xad,0x1250);c.emit(0x38,0xe9,8,0,0xaa)
    c.long(0xbf,0x7e4000);c.emit(0x29,0,0x70,0xc9,0,0x50);c.branch(0xf0,'found_map680')
    if neighbor:
        # Only the first map behind the blocked head tile. A variable scan
        # after sampling line252 would consume the bounded DMA deadline.
        c.absolute(0xad,0x1252);c.emit(0x18,0x69,8,0,0xaa)
        c.absolute(0xec,0x1250);c.branch(0xb0,'no_map680')
        c.long(0xbf,0x7e4000);c.emit(0x29,0,0x70,0xc9,0,0x50);c.branch(0xf0,'found_map680')
    else:
        # Retained diagnostic; not eligible for selection without a worst
        # eighth-record late-beam proof. No unbounded scan is permitted.
        c.absolute(0xae,0x1252);c.emit(0xa0,8,0)
        c.label('scan_map680');c.long(0xbf,0x7e4000);c.emit(0x29,0,0x70,0xc9,0,0x50);c.branch(0xf0,'found_map680')
        c.emit(0x8a,0x18,0x69,8,0,0xaa);c.absolute(0xec,0x1250);c.branch(0xb0,'no_map680')
        c.emit(0x88);c.branch(0xd0,'scan_map680')
    c.label('no_map680');c.jump('defer_beam')
    c.label('found_map680');c.long(0xbf,0x7e4004);c.emit(0xc9,128,4);c.branch(0x90,'length_map680')
    c.emit(0xa9,128,4);c.label('length_map680');c.emit(0xa8,0xe2,0x20);c.jump('map_beam_ok526')
    # Partial transfers retain the original shared range update. For a whole
    # interior record only, move the live head into the retired hole, then pop
    # that head. Mutation occurs AFTER actual MDMAEN return, never on selection.
    c.label('whole_map680');c.absolute(0xec,0x1252);c.branch(0xf0,'regular_map680')
    c.emit(0x8a,0x18,0x69,8,0);c.absolute(0xcd,0x1250);c.branch(0xf0,'regular_map680')
    c.emit(0x8a,0x18,0x69,0,0x40,0xa8);c.absolute(0xad,0x1252);c.emit(0x18,0x69,0,0x40,0xaa)
    c.emit(0xa9,7,0,0x8b,0x54,0x7e,0x7e,0xab);c.absolute(0xae,0x1252)
    c.label('regular_map680');c.emit(0x8a,0x18,0x69,8,0);c.jump('whole_continue680')
    start=body.index(bytes.fromhex('c220ad501238e90800aae220'),labels['selected526']-ORIGIN,labels['map_beam_ok526']-ORIGIN)
    body[start:start+3]=bytes([0x4c])+int(c.labels['late_map680']&65535).to_bytes(2,'little')
    whole=labels['whole526']-ORIGIN;assert body[whole:whole+5]==bytes.fromhex('8a18690800')
    body[whole:whole+5]=bytes([0x4c])+int(c.labels['whole_map680']&65535).to_bytes(2,'little')+b'\xea\xea'
    c.labels['whole_continue680']=labels['whole526']+5
    body.extend(c.finish());assert len(body)<=5984,len(body)
    return body,c.labels


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base',type=Path);p.add_argument('out',type=Path);p.add_argument('--neighbor',action='store_true');a=p.parse_args()
    r=client(a.base,a.out,extra_edit=lambda b,l:scan(b,l,neighbor=a.neighbor))
    r.update(candidate='progress680-neighbor' if a.neighbor else 'progress680-interior',interior_map_limit=1 if a.neighbor else 8,extra_DMA_stack_B=3)
    (a.out/'build.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('body_bytes','body_free','prefix_B','physical_free_B')}))
