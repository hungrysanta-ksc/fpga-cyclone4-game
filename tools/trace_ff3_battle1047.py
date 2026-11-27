"""Replay an FF3 checkpoint in the local Mesen reference, without modifying the SD files."""
import argparse
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import zlib


def attack_summary(patterns, frames):
    """Count the source patterns touched in moving frames, independent of SNES slot allocation."""
    record_size = 512 + 8192
    assert len(patterns) == 66 * record_size
    changed_screens = clean = clean_moving = repeated_tiles = referenced_tiles = 0
    previous = None
    for idx in range(66):
        start = idx * record_size
        used = patterns[start:start+512]
        ram = patterns[start+512:start+record_size]
        assert all(x in b'01' for x in used) and b'1' in used
        f = 509 + idx
        if previous is not None:
            fields = frames[f-1].split()
            moving = int(fields[4]) > 0
            no_writes = int(fields[6]) == 0
            if no_writes:
                assert ram == previous, f
            changed_screens += moving
            clean += no_writes
            clean_moving += no_writes and moving
            for tag, bit in enumerate(used):
                if bit == ord('1'):
                    src = slice(tag*16,(tag+1)*16)
                    referenced_tiles += 1
                    repeated_tiles += ram[src] == previous[src]
        previous = ram
    return dict(first=510, last=574, changed_screens=changed_screens, clean_frames=clean,
                moving_without_chr_writes=clean_moving, source_patterns=referenced_tiles,
                source_patterns_same_bytes_as_previous=repeated_tiles,
                first_580_without_chr_write=sum(int(x.split()[6])==0 for x in frames[:580]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('route', choices=('entry', 'attack'))
    for name in ('mesen', 'rom', 'slot', 'out'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    exe = args.mesen.resolve(strict=True)
    rom = args.rom.read_bytes()
    slot = args.slot.read_bytes()
    header = struct.unpack_from('<4s8I', slot)
    expected_serial = 3 if args.route == 'entry' else 4
    assert len(rom) == 524304 and zlib.crc32(rom) == 0x4be84aa7, 'The checkpoint is for the Korean release'
    assert header[:7] == (b'NESS', 1, 0x4be84aa7, 524288, 1, 21264, expected_serial)
    assert len(slot) == 21300 and zlib.crc32(slot[36:]) == header[7] and zlib.crc32(slot[:32]) == header[8]
    args.out.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[1]/'tests/nes-functional/ff3_battle_reference1047.lua'
    count = 2000 if args.route == 'entry' else 900
    with tempfile.TemporaryDirectory(prefix='ff3-reference-') as tmp:
        work = Path(tmp)
        (work/'game.nes').write_bytes(rom)
        (work/'slot.bin').write_bytes(slot[36:])
        script = work/'reference.lua'
        script.write_text(f'ROOT={json.dumps(work.as_posix())}\nBATTLE={str(args.route=="attack").lower()};LIMIT={count}\n'+source.read_text(), encoding='utf-8')
        with (args.out/'mesen.log').open('wb') as log:
            subprocess.run([exe, '--testRunner', '--nes.autoConfigureInput=false', '--nes.port1.type=NesController', script, work/'game.nes', '--timeout=180',
                            '--doNotSaveSettings', '--preferences.overrideSaveDataFolder=true',
                            '--preferences.saveDataFolder='+tmp, '--debug.scriptWindow.allowIoOsAccess=true'],
                           stdout=log, stderr=subprocess.STDOUT, cwd=work, timeout=200, check=True,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        lines = (work/'frames.txt').read_text().splitlines()
        assert len(lines) == count and lines[-1].split()[0] == str(count)
        shutil.copyfile(work/'frames.txt', args.out/'frames.txt')
        if args.route == 'entry':
            palettes = (work/'flash.hex').read_text().splitlines()
            assert len(palettes) == count
            masks = [int(line.split()[0],16) for line in palettes]
            burst = [0x1f,0x1e]*32
            start = next(i for i in range(count-len(burst)+1) if masks[i:i+len(burst)]==burst)
            selected = palettes[start:start+len(burst)]
            assert all(len(x.split())==33 for x in selected)
            (args.out/'flash.hex').write_text('\n'.join(selected)+'\n')
            print(f'Palette alternation: frames {start+1} to {start+len(burst)}')
        else:
            summary = attack_summary((work/'attack-patterns.bin').read_bytes(), lines)
            assert summary['changed_screens'] and summary['clean_frames']
            (args.out/'reference.json').write_text(json.dumps(summary,indent=2)+'\n')
            print(summary)


if __name__ == '__main__':
    main()
