"""Materialize pinned sd2snes and apply the reviewed C43 source overlay."""
import argparse,hashlib,io,json,shutil,subprocess,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--upstream',type=Path,help='Optional existing sd2snes clone (its working tree is ignored)');a=p.parse_args()
m=json.loads((ROOT/'source-manifest.json').read_text());u=m['upstreams']['sd2snes']
out=a.out.resolve()
if out.exists():raise SystemExit('Output must not already exist')
with tempfile.TemporaryDirectory(prefix='c43-upstream-') as td:
 repo=a.upstream.resolve() if a.upstream else Path(td)/'sd2snes'
 if not a.upstream:subprocess.run(['git','clone','--no-checkout',u['url'],str(repo)],check=True)
 cmd=['git','-c','safe.directory='+repo.as_posix(),'-C',str(repo)]
 data=subprocess.check_output(cmd+['archive',u['commit']])
 out.mkdir(parents=True)
 with tarfile.open(fileobj=io.BytesIO(data)) as t:
  for item in t.getmembers():
   if not item.isfile():continue
   f=out/item.name
   if not f.resolve().is_relative_to(out):raise SystemExit('Unsafe upstream archive path')
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(t.extractfile(item).read())
 for item in m['files']:
  name=item['path']
  if not name.startswith('src/firmware-overlay/'):continue
  source=ROOT/name
  if hashlib.sha256(source.read_bytes()).hexdigest()!=item['sha256']:raise SystemExit('Overlay hash mismatch: '+name)
  dst=out/name.removeprefix('src/firmware-overlay/');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dst)
 # The frozen build selected release VERSION rather than git describe.
 (out/'src/VERSION').write_text('RELEASE_VERSION = "1.11.2"\n')
print('Prepared',u['commit'],'with',len(m['firmware_overlay']),'MCU overlays')
