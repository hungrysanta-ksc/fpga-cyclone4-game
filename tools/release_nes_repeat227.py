# SPDX-License-Identifier: MIT
"""Package verified227 ARM + ROM-only FPGA; preserve ROM and restoration bytes."""
from pathlib import Path
import argparse,json,hashlib,zipfile
from nes_repeat227 import ROOT,BASE,sha

def read(p):return json.loads(p.read_bytes())
def digest(b):return hashlib.sha256(b).hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);out=p.parse_args().out
 assert not out.exists();d=BASE/'probes/nes-repeat227';e=read(d/'analysis.json')
 assert e['passed'] and e['trial_gates_pass'] and not e['new_fit']
 for n,h in e['gates'].items():assert sha(d/n)==h,n
 for n,h in e['public_sources'].items():assert sha(ROOT/n)==h,n
 prep=read(d/'arm01/preparation-repeat227.json')
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(d/'arm01'/n)==h,n
 c=read(d/'check02/result.json');assembly=read(d/'asm02/result227.json')
 fw=(d/'arm01/src/obj-nes-100/firmware.stm').read_bytes();fpga=(d/'asm02/fpga_n227.bi3').read_bytes()
 assert digest(fw)==c['firmware_sha256']==e['arm']['firmware_sha256']
 assert c['remaining_margin']==1800 and digest(fpga)==assembly['fpga_sha256']==e['fpga']['sha256']
 for marker in [b'NES GAME 227.nh1',b'game227.nes',b'fpga_n227.bi3',b'nes-progress-227.txt',b'nes-game-last-227.txt',b'nes-budget-227.txt',b'budget_schema=226']:
  assert marker in fw,marker
 old=BASE/'probes/nes-fast226/release01';oldz=old/'NES226-SMB3-PLANNERFAST.zip'
 assert sha(oldz)==read(old/'result.json')['zip_sha256']
 blobs={};preserved={}
 changed={'01-GAME227-SD-ROOT/sd2snes/firmware.stm','01-GAME227-SD-ROOT/sd2snes/fpga_n227.bi3'}
 with zipfile.ZipFile(oldz) as z:
  for n,item in read(old/'manifest.json')['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256']
   if n.startswith(('01-GAME226-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dest=n.replace('226','227') if n.startswith('01-') else n;blobs[dest]=b
    if dest not in changed:preserved[dest]=digest(b)
 blobs['01-GAME227-SD-ROOT/sd2snes/firmware.stm']=fw
 blobs['01-GAME227-SD-ROOT/sd2snes/fpga_n227.bi3']=fpga
 assert len(blobs['01-GAME227-SD-ROOT/sd2snes/nes/game227.nes'])>393216
 decision=dict(trial_ready=True,physical=False,fps60=False,new_fit=False,rom_only_update=True,
  arm_identity=227,wire_version='2231',snes_version='2271',budget_schema=226,run_ticks=6000,
  remaining_margin=1800,save_sram_unchanged=True,gbc164_unchanged=True)
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game227-ready.ko.md').read_bytes()
 blobs['decision227.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES227-SMB3-OAMREPEAT',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();out.mkdir(parents=True)
 zout=out/'NES227-SMB3-OAMREPEAT.zip'
 with zipfile.ZipFile(zout,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   i=zipfile.ZipInfo(n,(2026,10,18,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
 with zipfile.ZipFile(zout) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 result=dict(passed=True,decision=decision,zip_sha256=sha(zout),firmware_sha256=digest(fw),fpga_sha256=digest(fpga),
  preserved=preserved,baseline_zip_sha256=sha(oldz),evidence_sha256=sha(d/'analysis.json'),arm=e['arm'],
  public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_repeat227.py','docs/nes-game227-ready.ko.md']})
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 (out/'manifest.json').write_bytes(blobs['manifest.json'])
 (ROOT/'analysis/release227-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(passed=True,zip_sha256=result['zip_sha256'],decision=decision)))
if __name__=='__main__':main()
