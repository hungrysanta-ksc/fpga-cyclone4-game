"""Build private controlled replays of the last compact OBJ group on the MMC1027 board."""
import argparse
import hashlib
import json
import shutil
from binascii import crc_hqx
from pathlib import Path

from cross_nes1022 import GAMES, rom_path
from read_nes_tail1012 import decode

ROOT = Path(__file__).resolve().parents[1]
PROBES = ROOT.parent / 'probes'
WORK = PROBES / 'nes-kirby1028'
RATE = 21477.272  # NES master edges/ms

def overlay(board, out):
    src = (board / 'nes_e9_rows914.sv').read_text()
    # A validated compact E9 hint may look up a row before the first demand
    # miss. While unarmed, it may populate only a previously invalid entry.
    for old, new in [
        ('inspect=live&&armed&&', 'inspect=live&&'),
        ('spec=live&&armed&&', 'spec=live&&'),
        ('lookup[WIDTH-2:16]==hint_tag[13:LOW]', '(!armed || lookup[WIDTH-2:16]==hint_tag[13:LOW])'),
    ]:
        assert src.count(old) == 1
        src = src.replace(old, new)
    (out / 'nes_e9_rows914.sv').write_text(src)

def main(downloads, calendar):
    WORK.mkdir(exist_ok=True)
    overlay(PROBES / 'nes-kirby1027/board-tag', WORK)
    pins = json.loads((ROOT / 'analysis/kirby1027-hardware.json').read_text())['runs']
    plans = (PROBES / 'nes-kirby1023/arm/plans.txt').read_text().splitlines()
    cart=rom_path(downloads/'test','kirby').read_bytes()
    chr_start=16+512*bool(cart[6]&4)+16384*cart[4]
    assert bytes.fromhex((PROBES/'nes-kirby1023/arm/chr.hex').read_text())==cart[chr_start:]
    objs = {}
    for line in plans:
        frame, gen, length, crc, data = line.split(maxsplit=4)
        rec = bytes.fromhex(data)
        if frame == '3570' and rec[0] == 0x81:
            assert len(rec) == int(length) and crc_hqx(rec,65535) == int(crc,16)
            objs[int.from_bytes(rec[3:5], 'little')] = rec
    lines = [line.split() for line in calendar.read_text().splitlines()]
    cases = []
    for phase, (trial, target, frame_no) in enumerate([(1,1523,12),(2,1518,13),(2,1561,14)],1):
        path, = downloads.glob(f'nes-frame-mmc1027-{trial}*.bin')
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pins[trial-1]['sha256']['frame']
        row, = [r for r in decode(path.read_bytes(),1027)['rows'] if r['generation']==target]
        desc=bytes.fromhex(row['descriptor_hex'])
        size=int.from_bytes(desc[2:4],'little')
        slot=int.from_bytes(desc[4:6],'little')//32
        assert desc[:2]==b'\x01\x01' and (slot,size) in ((12,128),(10,192))
        recs=[objs[i] for i in range(slot,slot+size//32)]
        batch=b''.join(recs)
        (WORK/f'batch{phase}.hex').write_text('\n'.join(f'{b:02x}' for b in batch)+'\n')
        # Use the physical first-grant delay to place the consumer against a
        # fixed replay calendar. Phase 3 starts with only the last grant left.
        def grants(f):
            return [int(t) for k,t,fr,*_ in lines if k=='G' and int(fr)==f]
        prev, nxt, third = (grants(f) for f in range(frame_no,frame_no+3))
        assert prev and nxt and third
        times=[t-prev[0]+4000 for t in prev+nxt+third]
        stamps=row['last_slot_run']['ms_from_first_E9']
        wait=stamps['first_grant']-stamps['first_request']
        # Allow ~10 edges for the first cache miss to reach arbitration.
        release=times[len(prev)]-round(wait*RATE)-12 if phase<3 else times[len(prev)-1]-20
        assert release>0
        (WORK/f'grants{phase}.txt').write_text('\n'.join(map(str,times))+'\n')
        (WORK/f'case{phase}.txt').write_text(f'{len(batch)} {crc_hqx(batch,65535)} {len(recs)} {release} {times[len(prev)-1]}\n')
        cases.append(dict(phase=phase,gen=target,source_capture_frame=3570,slot=slot,bytes=size,
            physical_first_wait_ms=round(wait,4),physical_grant_to_done_ms=round(stamps['done']-stamps['first_grant'],4),
            replay_first_window=[times[0],times[len(prev)-1]],replay_consumer_release=release,
            prior_window_first_after_first_E9_estimate_ms=round(stamps['first_grant']-(nxt[0]-prev[0])/RATE,4) if phase<3 else None,
            sealed_before_previous_window='sensitivity only; final E9 seal and physical tag addresses absent from field trace'))
    (WORK/'inputs.json').write_text(json.dumps(dict(cases=cases,cartridge_sha256=GAMES['kirby'],
        candidate_source_sha256=hashlib.sha256((WORK/'nes_e9_rows914.sv').read_bytes()).hexdigest(),
        calendar_sha256=hashlib.sha256(calendar.read_bytes()).hexdigest()),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('downloads',type=Path)
    p.add_argument('calendar',type=Path)
    p.add_argument('--performance-board',action='store_true')
    p.add_argument('--arm',action='store_true')
    a=p.parse_args()
    main(a.downloads,a.calendar)
    if a.arm:
        from prepare_nes_trial802 import rename_edition
        parent=PROBES/'nes-kirby1025/link'
        src=WORK/'link/src'
        shutil.copytree(parent,src.parent)
        rename_edition(parent/'src',WORK/'edition',1025,1028)
        for file in (WORK/'edition').iterdir():
            shutil.copy2(file,src/file.name)
        budget=src/'nes_budget210.c'
        data=budget.read_bytes()
        assert data.count(b'edition=1025;')==1
        budget.write_bytes(data.replace(b'edition=1025;',b'edition=1028;'))
    if a.performance_board:
        baseline=PROBES/'nes-kirby1023/board'  # shipped in 1024 with the loader correction
        dest=WORK/'board-perf'
        shutil.copytree(baseline,dest)
        overlay(baseline,dest)
