"""Prepare pinned sd2snes with the reviewed C44 overlay, offline when bundled."""
import argparse, hashlib, io, json, shutil, subprocess, tarfile, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--out', type=Path, required=True)
p.add_argument('--upstream', type=Path, help='Existing sd2snes Git clone')
p.add_argument('--offline', action='store_true', help='Require the verified bundled upstream')
a = p.parse_args()
m = json.loads((ROOT / 'source-manifest.json').read_text())
u = m['upstreams']['sd2snes']
out = a.out.resolve()
if out.exists():
    raise SystemExit('Output must not already exist')
bundled = ROOT / 'upstream/sd2snes'
if a.offline and a.upstream:
    raise SystemExit('--offline and --upstream cannot be combined')
if a.offline and not bundled.is_dir():
    raise SystemExit('Bundled upstream missing; use the product source ZIP')
if bundled.is_dir() and not a.upstream:
    index = json.loads((ROOT / 'upstream-manifest.json').read_text())
    entries = index['components']['sd2snes']
    if entries['commit'] != u['commit']:
        raise SystemExit('Bundled upstream commit mismatch')
    expected = entries['files']
    actual = {f.relative_to(bundled).as_posix() for f in bundled.rglob('*') if f.is_file()}
    if actual != set(expected):
        raise SystemExit('Bundled upstream file list mismatch')
    for name, digest in expected.items():
        if hashlib.sha256((bundled / name).read_bytes()).hexdigest() != digest:
            raise SystemExit('Bundled upstream hash mismatch: ' + name)
    shutil.copytree(bundled, out)
else:
    with tempfile.TemporaryDirectory(prefix='c44-upstream-') as td:
        repo = a.upstream.resolve() if a.upstream else Path(td) / 'sd2snes'
        if not a.upstream:
            subprocess.run(['git', 'clone', '--no-checkout', u['url'], str(repo)], check=True)
        cmd = ['git', '-c', 'safe.directory=' + repo.as_posix(), '-C', str(repo)]
        data = subprocess.check_output(cmd + ['archive', u['commit']])
        out.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(data)) as t:
            for item in t.getmembers():
                if not item.isfile():
                    continue
                f = out / item.name
                if not f.resolve().is_relative_to(out):
                    raise SystemExit('Unsafe upstream archive path')
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(t.extractfile(item).read())
for item in m['files']:
    name = item['path']
    if not name.startswith('src/firmware-overlay/'):
        continue
    source = ROOT / name
    if hashlib.sha256(source.read_bytes()).hexdigest() != item['sha256']:
        raise SystemExit('Overlay hash mismatch: ' + name)
    dst = out / name.removeprefix('src/firmware-overlay/')
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dst)
(out / 'src/VERSION').write_text('RELEASE_VERSION = "1.11.2"\n')
print('Prepared', u['commit'], 'with', len(m['firmware_overlay']), 'MCU overlays')
