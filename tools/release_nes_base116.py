# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,zipfile,shutil
from nes_spi_boot import ROOT,sha
from nes_pair109 import verify,digest
from stage_nes_trial110 import FILES,PAIR

FIRMWARE='88b632c87e3c164ef517603428af08b830a6a7a131bd63675b92a79ad44b987d'
def main():
 p=argparse.ArgumentParser()
 for n in ['pair','firmware','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();assert verify(a.pair,PAIR)['pair_identity_pass']
 assert sha(a.firmware)==FIRMWARE and a.firmware.stat().st_size==185680
 roles={}
 for n,role in FILES.items():
  if n.startswith('review-only/trial/') and Path(n).name not in ['firmware.stm','fpga_n86.bi3','fpga_base.bi3','m3nu.bin']:continue
  roles[n.replace('review-only/trial/','01-BASE-SD-ROOT/').replace('review-only/restore/','02-RESTORE044-SD-ROOT/')]=role
 blobs={n:(a.firmware if role=='arm108.stm' else a.pair/'files'/role).read_bytes() for n,role in roles.items()}
 roles['01-BASE-SD-ROOT/sd2snes/firmware.stm']='arm116.stm'
 blobs['01-BASE-SD-ROOT/NES BASE 116.nh1']=b''
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-base116-instructions.ko.md').read_bytes()
 blobs['decision116.json']=(json.dumps(dict(candidate='NES-BASE-116',firmware_version='CF86-BASE116',scope='configureCF86/emptySTOP/base restore/menu return only; no ROM payload/RUN',authorization='user requested continuation after full80 load/readback/STOP pass and BASE_START-only recovery failure; narrow restoration probe',attempts=1,human_limit_seconds=60,physical_result='pending',full_nes_installable=False,start_enabled=False,electrical_signoff=False,common_cause_8us_proven=False),indent=2)+'\n').encode()
 m=dict(candidate='NES-BASE-116',unchanged_pair_reference=PAIR,files={n:dict(bytes=len(b),sha256=digest(b),role=roles.get(n)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(m,indent=2)+'\n').encode()
 a.out.mkdir(parents=True);zpath=a.out/'NES116-BASE-RECOVERY-and-RESTORE044.zip'
 with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,9,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(zpath) as z:
  assert len(z.namelist())==11 and set(z.namelist())==set(blobs)
  assert not any(n.endswith('.nes') for n in z.namelist())
  for n,b in blobs.items():assert z.read(n)==b,n
 result=dict(zip_sha256=sha(zpath),zip_bytes=zpath.stat().st_size,members=11,firmware_sha256=FIRMWARE,firmware_bytes=185680,unchanged_roles=6,physical=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');(a.out/'manifest.json').write_bytes(blobs['manifest.json']);shutil.copy2(__file__,a.out/'executed-release116.py');print(json.dumps(result))
if __name__=='__main__':main()
