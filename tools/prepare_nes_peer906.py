"""Prepare an isolated OBJ row-pair experiment against the fitted MMC905 sources."""
import json
import shutil
import sys
from pathlib import Path
from read_nes_supply905 import decode
from nes_raw506 import once, sha
from prepare_nes_opening818 import ADVENTURE_SHA


def prepare(temp, out, trace, rom):
    board = temp/'nes-trial816-board905'
    out.mkdir(parents=True,exist_ok=True)
    src = (board/'nes_source_tile192.sv').read_text()
    src = once(src, '.second_plane(bg_word),', '.second_plane(bg_word),.from_rom(arb_response),')
    (out/'nes_source_tile192.sv').write_text(src,newline='\n')
    tile = (board/'nes_tile205.sv').read_text()
    tile = once(tile, 'input wire [7:0] second_plane,','input wire from_rom,input wire [7:0] second_plane,')
    tile = once(tile, ' reg [7:0] peer_byte;', ''' reg [7:0] peer_byte;
 reg use_obj_peer;
 // Only the physical response for the low plane of this short OBJ row
 // carries its paired byte. A capture hit, masked row or abort cannot reuse it.''')
    tile = once(tile, 'state<=IDLE;kind_q<=0;', "use_obj_peer<=0;state<=IDLE;kind_q<=0;")
    tile = once(tile, 'FETCH:if(zero_byte)begin held_byte<=0;', 'FETCH:if(zero_byte)begin use_obj_peer<=0;held_byte<=0;')
    tile = once(tile, 'held_byte<=response_data;peer_byte<=second_plane;',
                'use_obj_peer<=from_rom && kind==1 && EXTERNAL_PLAN!=0 && plan_short;held_byte<=response_data;peer_byte<=second_plane;')
    tile = once(tile, 'if(pair_bg && !index[0])','if((pair_bg || use_obj_peer) && !index[0])')
    (out/'nes_tile205.sv').write_text(tile,newline='\n')
    assert sha(rom)==ADVENTURE_SHA
    chr_data=rom.read_bytes()[-131072:]
    # Distinct real CHR tiles, with known offsets. MMC905 did not record tags.
    (out/'chr.hex').write_text(''.join(f'{b:02x}\n' for b in chr_data[0x18000:0x18200]))
    row, = [r for r in decode(trace)['rows'] if 'detail' in r]
    chunks=row['detail']
    (out/'counts.hex').write_text(''.join(f"{t['grants']:02x}\n" for c in chunks for t in c['tiles']))
    assert [c['bytes'] for c in chunks]==[16,160,64,608,32,32,32,32]
    cal=temp/'nes-service509-rom03/fill1'
    anchors=dict(tuple(map(int,l.split())) for l in (cal/'anchors.tsv').read_text().splitlines())
    offset=anchors[12]-8
    grants=[int(l.split()[1])-offset for l in (cal/'rom.tsv').read_text().splitlines() if l.startswith('G ')]
    (out/'calendar.txt').write_text(''.join(f'{v}\n' for v in grants))
    (out/'period.svh').write_text(f'localparam PERIOD={anchors[20]-anchors[12]}, N={len(grants)};\n')
    print(json.dumps(dict(trace=sha(trace),game=sha(rom),generation=row['generation'],calendar=sha(cal/'rom.tsv'))))


def fit_board(temp):
    from prepare_nes_frame900 import QUARTUS, fit
    src=temp/'nes-trial816-board905'
    dst=temp/'nes-trial816-board906'
    dst.mkdir()
    for sub in ('rtl','sys'):
        shutil.copytree(src/sub,dst/sub)
    for f in src.iterdir():
        if f.suffix in ('.sv','.v','.vhd','.qsf','.qpf','.sdc','.tcl','.hex'):
            shutil.copyfile(f,dst/f.name)
    for name in ('nes_source_tile192.sv','nes_tile205.sv'):
        shutil.copyfile(temp/'nes-peer906/pair'/name,dst/name)
    fit(temp,906,QUARTUS)


if __name__=='__main__':
    if sys.argv[1]=='fit':
        fit_board(Path(sys.argv[2]))
    else:
        prepare(*(Path(s) for s in sys.argv[1:]))
