"""Archive reviewed project sources and the pinned upstream build inputs."""
import argparse, hashlib, io, json, subprocess, tarfile, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--sd2snes', type=Path, required=True)
p.add_argument('--gameboy', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
if a.out.exists():
    raise SystemExit('Refusing to overwrite an existing source archive')

def git(repo, *args):
    return subprocess.check_output(['git', '-c', 'safe.directory=' + repo.as_posix(),
                                    '-C', str(repo), *args])

def extract(data):
    result = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        for member in t.getmembers():
            if member.isfile():
                if member.name.startswith('/') or '..' in Path(member.name).parts:
                    raise SystemExit('Unsafe archive path')
                result[member.name] = t.extractfile(member).read()
    return result

commit = git(ROOT, 'rev-parse', 'HEAD').decode().strip()
payload = extract(git(ROOT, 'archive', commit))
m = json.loads(payload['source-manifest.json'])
index = {'components': {}}
selections = {
    'sd2snes': (a.sd2snes, ['LICENSE', 'README.md', 'src', 'utils', 'verilog/sd2snes_mini']),
    'Gameboy_MiSTer': (a.gameboy, [
        'ReadMe.md', 'BootROMs/README.md', 'BootROMs/Makefile', 'BootROMs/CGB_logo.png',
        'BootROMs/src/cgb_boot.asm', 'BootROMs/src/hardware.inc',
        'BootROMs/src/logo-compress.c'])
}
for name, (repo, paths) in selections.items():
    upstream = m['upstreams'][name]
    files = extract(git(repo.resolve(), 'archive', upstream['commit'], '--', *paths))
    for path, data in files.items():
        if Path(path).suffix.lower() in {'.exe', '.bin', '.bit', '.rbf', '.bi3', '.gb', '.gbc', '.sav', '.srm'}:
            raise SystemExit('Unexpected binary build input: ' + path)
        payload['upstream/' + name + '/' + path] = data
    index['components'][name] = {
        'url': upstream['url'], 'commit': upstream['commit'],
        'files': {n: hashlib.sha256(b).hexdigest() for n, b in sorted(files.items())}
    }
payload['upstream-manifest.json'] = (json.dumps(index, indent=2) + '\n').encode()
payload['PRODUCT.json'] = (json.dumps({
    'product': 'sd2snesHST', 'version': '0.9.0', 'candidate': 'G13C44',
    'implementation_commit': '35ef4aef14fc6abef6495a980b7f00f257e5174f',
    'source_commit': commit, 'guide': 'docs/SOURCE-BUNDLE.ko.md'
}, indent=2) + '\n').encode()
for entry in m['files']:
    if hashlib.sha256(payload[entry['path']]).hexdigest() != entry['sha256']:
        raise SystemExit('Runtime source hash changed: ' + entry['path'])
payload['BUNDLE-SHA256SUMS.txt'] = ''.join(
    hashlib.sha256(b).hexdigest() + '  ' + n + '\n'
    for n, b in sorted(payload.items())).encode()
prefix = 'sd2snesHST-v0.9.0-source/'
a.out.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(a.out, 'w', zipfile.ZIP_DEFLATED) as z:
    for name, data in sorted(payload.items()):
        item = zipfile.ZipInfo(prefix + name, date_time=(2026, 10, 4, 0, 0, 0))
        item.compress_type = zipfile.ZIP_DEFLATED
        item.external_attr = 0o644 << 16
        z.writestr(item, data)
with zipfile.ZipFile(a.out) as z:
    if z.testzip():
        raise SystemExit('Archive CRC failed')
print(json.dumps({'source_commit': commit, 'source_hashes': len(m['files']),
    'upstream_files': {k: len(v['files']) for k, v in index['components'].items()},
    'bytes': a.out.stat().st_size, 'sha256': hashlib.sha256(a.out.read_bytes()).hexdigest()}, indent=2))
