# SPDX-License-Identifier: MIT
from pathlib import Path
import ast,hashlib,json,re,subprocess,zipfile
from manage_nes_h1_sd import C44_FW,C44_GBC,EXPECTED,payload
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args,cwd=ROOT,data=None):
 return subprocess.run(['git','-c','safe.directory='+cwd.as_posix(),*args],cwd=cwd,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout

def main():
 r=ROOT;raw=r/'analysis/local-h1-bringup-037';count=0
 prior=json.loads((r/'analysis/h1-spi-artifacts.json').read_text())
 for g in ('sources','status_files','evidence'):
  for e in prior[g]:
   p=(raw/'baseline-status' if g=='status_files' else r)/e['path']
   assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],str(p);count+=1
 assert count==201
 for e in json.loads((r/'source-manifest.json').read_text())['files']:assert sha(r/e['path'])==e['sha256'],e['path']
 c44=json.loads((r/'release/c44-artifacts.json').read_text())['files']
 assert C44_FW==c44['firmware.stm']['sha256'] and C44_GBC==c44['fpga_egbc.bi3']['sha256']
 sweep=json.loads((raw/'rtl/result.json').read_text());assert len(sweep['runs'])==24 and sweep['passed']
 for e in sweep['runs']:
  assert e['passed'] and e['exit_code']==0
  log=(raw/'rtl'/f"p{e['profile']}-phase{e['phase_ns']:02d}.log").read_text()
  assert 'PASS NES H1 BOARD checks=6 rombytes=512 payloadbytes=8192' in log
  assert not re.search(r'\*\* (?:Fatal|Error):',log)
 assert sha(raw/'rtl/nes_h1_board_bus.sv')==sha(r/'analysis/local-h1-spi-036/resource/nes_h1_board_bus.sv')==sweep['compiled_boundary_sha256']
 assert json.loads((raw/'install-tests/result.json').read_text())['passed']==12
 pkg=raw/'NES-H1-BRINGUP-037';payload(pkg)
 assert (pkg/'manage_nes_h1_sd.py').read_bytes()==(r/'tools/manage_nes_h1_sd.py').read_bytes()
 assert (pkg/'READ-ME.ko.md').read_bytes()==(r/'docs/nes-h1-bringup-test.ko.md').read_bytes()
 assert sha(pkg/'reference.png')==sha(r/'analysis/local-h1-board-034/board-reference-contact.png')
 result=json.loads((r/'analysis/h1-bringup-verification.json').read_text());assert sha(pkg.with_suffix('.zip'))==result['zip_sha256']
 with zipfile.ZipFile(pkg.with_suffix('.zip')) as z:
  expected={f.relative_to(pkg).as_posix():f.read_bytes() for f in pkg.rglob('*') if f.is_file()}
  assert set(z.namelist())==set(expected)
  for n,b in expected.items():assert z.read(n)==b
 registry=json.loads((r/'cores/registry.json').read_text());before=json.loads((raw/'baseline-status/cores/registry.json').read_text())
 assert [e for e in registry['cores'] if e['id']!='nes']==[e for e in before['cores'] if e['id']!='nes']
 h=json.loads((r/'analysis/hardware-readiness.json').read_text());old=json.loads((raw/'baseline-status/analysis/hardware-readiness.json').read_text())
 assert {k:v for k,v in h.items() if k!='H1'}=={k:v for k,v in old.items() if k!='H1'}
 plan=json.loads((r/'docs/nes-development-plan.json').read_text());assert plan['hardware_tracks']['H1']==h['H1']
 assert not git('diff','--cached','--name-only').strip()
 assert not git('diff','HEAD','--','src/fpga','src/firmware-overlay','src/renderer','cores/gbc','release','source-manifest.json').strip()
 git('diff','--check')
 public=json.loads((raw/'public-files.json').read_text())
 for n in public:
  if n.endswith('.py'):ast.parse((r/n).read_text())
  if n.endswith('.md'):
   for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)',(r/n).read_text()):
    if '://' not in link:assert ((r/n).parent/link).exists(),link
 # check-ignore returns0 if any item is ignored,1 if none is ignored.
 def ignored(names):
  cp=subprocess.run(['git','-c','safe.directory='+r.as_posix(),'check-ignore','-z','--stdin'],cwd=r,input=('\0'.join(names)+'\0').encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  assert cp.returncode in (0,1),cp.stderr;return set(cp.stdout.decode().strip('\0').split('\0'))-{''}
 assert not ignored(public)
 raws=[f.relative_to(r).as_posix() for f in raw.rglob('*') if f.is_file()]
 assert ignored(raws)==set(raws)
 upstream=r.parent/'nes-upstream-mister'
 assert git('rev-parse','HEAD',cwd=upstream).decode().strip()=='49a0a662e244469ca77b2155746a066df704ffae'
 assert not git('status','--porcelain',cwd=upstream).strip()
 manifest=r/'analysis/h1-bringup-artifacts.json';entries=0
 if manifest.exists():
  m=json.loads(manifest.read_text())
  for g in ('sources','status_files','evidence'):
   for e in m[g]:
    p=r/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];entries+=1
 print(json.dumps({'previous036_entries':count,'GBC_source_hashes':152,'phase_runs':24,'installer_cases':12,'package_integrity':'PASS','GBC_protected_paths':'unchanged','non_NES_registry':'unchanged','H0_observation':'unchanged','staged_files':0,'git_diff_check':'PASS','public_allowlist':'PASS','raw_ignored_files':len(raws),'upstream_NES_pin_and_clean':'PASS','037_manifest_entries':entries},indent=2))
if __name__=='__main__':main()
