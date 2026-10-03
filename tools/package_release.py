"""Package the tested C44 runtime allowlist, matching source reference and guide."""
import argparse,hashlib,json,re,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--payload',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args()
if not re.fullmatch(r'[0-9a-f]{40}',a.source_commit):raise SystemExit('Use the full, reviewed source commit SHA')
out=a.out.resolve();archive=out.with_suffix('.zip')
if out.exists()or archive.exists():raise SystemExit('Refusing to replace an existing release')
m=json.loads((ROOT/'release/c44-artifacts.json').read_text())
allowed={'firmware.stm','fpga_egbc.bi3','gbc_snes.bin','gbc-utc-offset.txt'}
if set(m['files'])!=allowed:raise SystemExit('Unexpected runtime allowlist')
# Validate all inputs before creating the output.
payload={}
for name,meta in m['files'].items():
 data=(a.payload/name).read_bytes()
 if len(data)!=meta['bytes']or hashlib.sha256(data).hexdigest()!=meta['sha256']:raise SystemExit('Payload differs from tested C44: '+name)
 payload['sd2snes/'+name]=data
docs=['USER-GUIDE.ko.md','COMPATIBILITY.ko.md','RELEASE-C44.ko.md','DEPENDENCY-REGISTER.ko.md','BUILD-C44.ko.md']
for name in docs:payload['docs/'+name]=(ROOT/'docs'/name).read_bytes()
for name in ['sd2snes-COPYING','GPL-3.0.txt','SameBoy-MIT.txt','T80.vhd.notice.txt','gb.v.notice.txt','gbc_pll0.v.notice.txt']:
 payload['licenses/'+name]=(ROOT/'licenses'/name).read_bytes()
for name in ['c44-artifacts.json','c44-verification.json','c44-rebuild-verification.json']:
 payload['verification/'+name]=(ROOT/'release'/name).read_bytes()
payload['Verify-SD.ps1']=(ROOT/'tools/Verify-SD.ps1').read_bytes()
payload['SOURCE.txt']=('Source commit: '+a.source_commit+'\nhttps://github.com/hungrysanta-ksc/fpga-cyclone4-game/tree/'+a.source_commit+'\nBuild: docs/BUILD-C44.ko.md\n').encode()
payload['START-HERE.ko.md']=('# FXPAK Pro GBC C44 업데이트\n\n[사용 가이드](docs/USER-GUIDE.ko.md)를 먼저 읽어 주세요.\n\n정상 설치된 공식 1.11.2 계열 SD에 파일을 합쳐 복사하는 업데이트입니다. 전원을 끄고 기존 sd2snes 폴더와 세이브를 백업한 후 적용합니다.\n\nsd2snes 폴더의 실행 파일 3개와 시차 설정을 사용합니다. 기존 gbc-utc-offset.txt 값이 정확하면 그 값을 유지하세요. 동봉 +540은 한국/일본 현지 시각용입니다.\n\nSGB 코어·BIOS, 게임·세이브는 포함하지 않습니다. 기존 SD의 다른 파일은 유지합니다. C43 사용자는 firmware.stm만 교체해도 됩니다.\n\n이 ZIP은 C44 실기 성공 바이너리로 구성한 배포 준비본입니다. 최종 공개 릴리스 발행 상태는 저장소에서 확인하세요.\n').encode('utf-8')
for name in payload:
 if Path(name).suffix.lower()in ['.gb','.gbc','.egbc','.sav','.srm','.g13d','.exe']or 'sgb'in Path(name).name.lower():raise SystemExit('Forbidden member: '+name)
payload['SHA256SUMS']=''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n'for name,data in sorted(payload.items())).encode('ascii')
out.mkdir(parents=True)
for name,data in payload.items():
 f=out/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
 for name,data in sorted(payload.items()):
  info=zipfile.ZipInfo(name,date_time=(2026,10,4,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,data)
with zipfile.ZipFile(archive)as z:
 if z.testzip():raise SystemExit('Archive CRC failed')
 for name,data in payload.items():
  if z.read(name)!=data:raise SystemExit('Archive payload mismatch')
print(json.dumps(dict(file=archive.name,bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),members=len(payload),source_commit=a.source_commit),indent=2))
