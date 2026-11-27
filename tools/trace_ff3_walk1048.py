"""Replay held Down from the serial-8 FF3 town save in the Korean reference ROM."""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('mesen', 'rom', 'slot', 'out'):
        ap.add_argument(name, type=Path)
    ap.add_argument('--frames',type=int,nargs='+',default=[])
    ap.add_argument('--serial',type=int,default=8,help='Required sequence number of the supplied slot')
    ap.add_argument('--route', type=Path, help='Timed controller inputs and screenshot frame numbers')
    args = ap.parse_args()
    route = json.loads(args.route.read_text()) if args.route else None
    out = args.out.resolve()
    rom, slot = args.rom.read_bytes(), args.slot.read_bytes()
    assert hashlib.sha256(rom).hexdigest() == 'f4e33d48c474a9ac7d945d1bafcdcaf01fec9b7d78257357c574b9661ccdd1b5'
    assert struct.unpack_from('<4s6I', slot) == (b'NESS', 1, zlib.crc32(rom), 524288, 1, 21264, args.serial)
    assert len(slot) == 21300 and struct.unpack_from('<II', slot, 28) == (zlib.crc32(slot[36:]), zlib.crc32(slot[:32]))
    tests = Path(__file__).resolve().parents[1]/'tests/nes-functional'
    init = (tests/'ff3_battle_reference1047.lua').read_text().split('local f=-118;', 1)[0]
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ff3-walk-') as tmp:
        work = Path(tmp)
        (work/'slot.bin').write_bytes(slot[36:])
        (work/'game.nes').write_bytes(rom)
        script = work/'walk.lua'
        walk=(tests/'ff3_walk1048.lua').read_text()
        if route:
            buttons = []
            for start,end,key in route['inputs']:
                assert 0 < start <= end <= route['end'] and key in ('start','select','up','down','left','right','a','b')
                buttons.append(f"if f>={start} and f<={end} then keys.{key}=true end")
            walk=walk.replace('emu.setInput({down=f>=15},0)', 'local keys={};'+';'.join(buttons)+';emu.setInput(keys,0)')
            screens=set(route['screens']) | set(args.frames)
            test=' or '.join(f'f=={i}' for i in sorted(screens)) or 'false'
            walk=walk.replace('f==8 or f%30==0 or (f>=180 and f<=290 and f%4==0)',test)
            walk=walk.replace('f==900 then',f"f=={route['end']} then")
        if args.frames:
            # Keep the existing PPU evidence layout, in route-relative frame numbers.
            raw=(tests/'capture_geometry230.lua').read_text()
            begin=raw.index('if CAP_FIRST>0 then\n')
            end=raw.index('\nend\nlocal function input',begin)
            hooks=raw[begin+len('if CAP_FIRST>0 then\n'):end].replace('emu.addMemoryCallback(', 'track(')
            hooks=hooks.replace('s.frameCount','captureFrame')
            setup=raw[raw.index('local fetches='):raw.index('emu.addEventCallback(')]
            setup=setup.replace('local writes=', 'local bus_writes=')
            hooks=hooks.replace('writes:write','bus_writes:write')
            setup=setup.replace('return CAP_FIRST>0 and captureFrame>=CAP_FIRST and captureFrame<=CAP_LAST','return wanted[captureFrame]')
            setup='local OUT_DIR=ROOT;local captureFrame=0;local wanted={'+','.join(f'[{i}]=true' for i in args.frames)+'}\n'+setup
            setup+='''local handles={}
local function track(fn,...)
 local args={...};handles[#handles+1]={emu.addMemoryCallback(fn,table.unpack(args)),args}
end
local function install()
'''+hooks+'''
end
emu.addEventCallback(function()
 captureFrame=f+1
 if wanted[captureFrame] and #handles==0 then install()
 elseif not wanted[captureFrame] and #handles>0 then
  for _,h in ipairs(handles) do emu.removeMemoryCallback(h[1],table.unpack(h[2])) end
  handles={}
 end
end,emu.eventType.startFrame)
'''
            walk=walk.replace('local f=-118','local f=-118\n'+setup)
            walk=walk.replace('f=f+1','if #chunks>0 then fetches:write(table.concat(chunks));chunks={} end\n f=f+1')
            walk=walk.replace('if f==8 or','if wanted[f] or f==8 or')
            walk=walk.replace('trace:close();','fetches:close();bus_writes:close();nt:close();rows:close();trace:close();')
        script.write_text(f'ROOT={json.dumps(work.as_posix())}; OUTPUT=ROOT; BATTLE=false\n'+init+walk, encoding='utf-8')
        with (out/'mesen.log').open('wb') as log:
            subprocess.run([args.mesen.resolve(), '--testRunner','--nes.autoConfigureInput=false','--nes.port1.type=NesController',
                            script,work/'game.nes','--timeout=480','--enableStdout','--doNotSaveSettings','--debug.scriptWindow.allowIoOsAccess=true',
                            '--preferences.overrideSaveDataFolder=true','--preferences.saveDataFolder='+tmp],
                           cwd=work, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=510)
        for path in [work/'walk.tsv',work/'chr-tiles.tsv', *work.glob('*.ppm')]:
            shutil.copyfile(path,out/path.name)
        if args.frames:
            for name in ('ppu-fetch.bin','nametable.bin','rows.bin','writes.bin'):
                shutil.copyfile(work/name,out/name)
            shutil.copyfile(work/'walk.tsv',out/'frames.tsv')
            for f in args.frames:
                pixels=(work/f'{f:03}.ppm').read_bytes().split(b'\n',3)[3]
                (out/f'frame-{f:04}.rgb').write_bytes(pixels)
            (out/'capture.json').write_text(json.dumps(dict(exit_code=0,capture_first=min(args.frames),
                capture_last=max(args.frames),sampled=args.frames)))
    assert len((out/'walk.tsv').read_text().splitlines())==(1+route['end'] if route else 901)

if __name__=='__main__':
    main()
