"""Preserve selected and rejected693 evidence without private license material."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(a):
    a.out.mkdir(parents=True, exist_ok=False)
    files = {}
    for f in a.probe.rglob('*'):
        if not f.is_file() or a.out in f.parents:
            continue
        r = f.relative_to(a.probe)
        if r.parts[0].startswith('archive') or '__pycache__' in r.parts:
            continue
        if any(x in f.name.lower() for x in ('license', 'wrapper')) or f.name == 'rtl.ps1':
            continue
        if (len(r.parts) == 1 or r.parts[0].startswith(('patch', 'client', 'cpu', 'base'))
                or f.suffix in ('.c', '.h', '.inc', '.su', '.log', '.ld', '.mk', '.json')
                or f.name in ('Makefile', 'firmware.stm', 'sd2snes.elf', 'sd2snes.map')):
            files['candidate/' + r.as_posix()] = f
    for d in sorted(a.traces.glob('nes-longrun693-*')):
        if not d.is_dir() or not d.name.startswith(('nes-longrun693-cpu', 'nes-longrun693-rtl')):
            continue
        for f in d.rglob('*'):
            if not f.is_file() or 'work' in f.parts or '__pycache__' in f.parts:
                continue
            if any(x in f.name.lower() for x in ('license', 'wrapper')):
                continue
            files['runs/' + d.name + '/' + f.relative_to(d).as_posix()] = f
    for f in Path('tools').glob('*longrun693.py'):
        files[f.as_posix()] = f
    for n in ('check_nes_longrun693_cpu.py', 'check_nes_longrun693_rtl.py'):
        f = Path('tools') / n
        files[f.as_posix()] = f
    for n in ('analysis/longrun693-verification.json', 'docs/nes-longrun693-results.ko.md'):
        files[n] = Path(n)
    assert not any(any(x in n.lower() for x in ('license', 'wrapper', 'float-private')) for n in files)
    manifest = {n: dict(bytes=f.stat().st_size, SHA256=sha(f)) for n, f in sorted(files.items())}
    (a.out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf8')
    archive = a.out / 'evidence.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as z:
        for n, f in sorted(files.items()):
            z.write(f, n)
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist()) == set(manifest)
        for n, v in manifest.items():
            b = z.read(n)
            assert len(b) == v['bytes'] and hashlib.sha256(b).hexdigest() == v['SHA256'], n
    report = dict(stage=693, location='WORKSPACE/probes/nes-longrun693/' + a.out.name,
                  files=len(files), bytes=archive.stat().st_size, SHA256=sha(archive),
                  manifest_SHA256=sha(a.out / 'manifest.json'), all_extracted_bytes_verified=True,
                  private=True, license_files_included=False,
                  selected='patch04/arm03+client02;guards08/menu03/base03-*;cpu05/rtl01',
                  inventory=manifest)
    a.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print('PASS693 archive:', len(files), 'files, all bytes rehashed; private license material excluded')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for n in ('probe', 'traces', 'out', 'report'):
        p.add_argument('--' + n, type=Path, required=True)
    main(p.parse_args())
