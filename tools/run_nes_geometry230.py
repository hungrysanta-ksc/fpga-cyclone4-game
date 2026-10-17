# SPDX-License-Identifier: MIT
"""Supplement the pinned229 workload with observed NT/attribute fetches and row state; no ROM patches or RAM writes.

Emulator evidence only, not the deployed FPGA collector or hardware timing.
ROM and raw game artifacts remain local and must not enter Git.
"""
from pathlib import Path
import argparse, hashlib, json, os, subprocess

ROOT = Path(__file__).resolve().parents[1]
ROM_SHA = 'dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    for n in ('rom', 'mesen', 'out'):
        p.add_argument('--'+n, type=Path, required=True)
    p.add_argument('--frames', type=int, default=1200)
    p.add_argument('--capture-first', type=int, default=0)
    p.add_argument('--capture-last', type=int, default=0)
    a = p.parse_args()
    assert sha(a.rom) == ROM_SHA, 'Wrong user ROM; do not silently substitute region/revision'
    d = a.out.resolve(); assert str(d).isascii()
    d.mkdir(parents=True, exist_ok=False)
    script = ROOT/'tests/nes-functional/capture_geometry230.lua'
    assert (a.capture_first == a.capture_last == 0) or (0<a.capture_first<=a.capture_last<a.frames)
    config = (f'local OUT_DIR={json.dumps(d.as_posix())}\nlocal END_FRAME={a.frames}\n'
              f'local CAP_FIRST={a.capture_first}\nlocal CAP_LAST={a.capture_last}\n')
    (d/'capture.lua').write_text(config+script.read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
    # A private name isolates emulator-generated files from the user's ROM.
    (d/'geometry230-local.nes').write_bytes(a.rom.read_bytes())
    env = os.environ.copy(); env['DOTNET_ROOT'] = env['DOTNET_ROOT_X64'] = 'C:/works/dotnet'
    command = [str(a.mesen.resolve()), '--testRunner', str(d/'capture.lua'),
               str(d/'geometry230-local.nes'), '--timeout=300', '--doNotSaveSettings', '--enableStdout',
               '--debug.scriptWindow.allowIoOsAccess=true']
    with (d/'mesen.log').open('wb') as log:
        run = subprocess.run(command, cwd=d, env=env, stdout=log, stderr=subprocess.STDOUT,
                             timeout=330, creationflags=subprocess.CREATE_NO_WINDOW)
    result = dict(exit_code=run.returncode, rom_sha256=ROM_SHA,
                  script_sha256=sha(script), runner_sha256=sha(Path(__file__)),
                  emulator_sha256=sha(a.mesen), core_sha256=sha(a.mesen.parent/'MesenCore.dll'),
                  scope=__doc__, physical=False, rom_modified=False,
                  capture_first=a.capture_first, capture_last=a.capture_last)
    (d/'capture.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    assert run.returncode == 0, (d/'mesen.log').read_text(errors='replace')[-5000:]
    print(json.dumps(result))

if __name__ == '__main__':
    main()
