# SPDX-License-Identifier: MIT
"""Package unchanged ARM116 with the pinned synthetic80 fixture and044 restore."""
from pathlib import Path
import argparse,json,zipfile
from nes_spi_boot import ROOT,sha
from nes_pair109 import verify,digest
from stage_nes_trial110 import FILES,PAIR
from release_nes_base116 import FIRMWARE

def main():
 p=argparse.ArgumentParser()
 for n in ['pair','firmware','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 assert verify(a.pair,PAIR)['pair_identity_pass']
 assert sha(a.firmware)==FIRMWARE and a.firmware.stat().st_size==185680
 roles={n.replace('review-only/trial/','01-FULL80-SD-ROOT/').replace('review-only/restore/','02-RESTORE044-SD-ROOT/'):role for n,role in FILES.items()}
 blobs={n:(a.firmware if role=='arm108.stm' else a.pair/'files'/role).read_bytes() for n,role in roles.items()}
 roles['01-FULL80-SD-ROOT/sd2snes/firmware.stm']='arm116.stm'
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-full118-instructions.ko.md').read_bytes()
 decision=dict(package='NES-FULL80-118',firmware_version='CF86-BASE116',firmware_rebuilt=False,marker='NES VERIFY 094 80.nh1',progress='/sd2snes/nes-progress-116.txt',report='/sd2snes/nes-verify-last-094.txt',scope='synthetic80 load/readback/STOP/base/menu; no RUN',attempts=1,human_observation_limit_seconds=600,physical_full116_result='pending',short116_menu_return='user confirmed; log117',full_nes_installable=False,start_enabled=False,electrical_signoff=False,common_cause_8us_proven=False)
 blobs['decision118.json']=(json.dumps(decision,indent=2)+'\n').encode()
 m=dict(package='NES-FULL80-118',unchanged_pair_reference=PAIR,files={n:dict(bytes=len(b),sha256=digest(b),role=roles.get(n)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(m,indent=2)+'\n').encode()
 assert len(blobs)==12
 assert [n for n in blobs if n.endswith('.nes')]==['01-FULL80-SD-ROOT/sd2snes/nes/fine_x.nes']
 assert [n for n in blobs if n.endswith('.nh1')]==['01-FULL80-SD-ROOT/NES VERIFY 094 80.nh1']
 a.out.mkdir(parents=True);archive=a.out/'NES118-FULL80-ARM116-and-RESTORE044.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,9,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert len(z.namelist())==len(blobs) and set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 result=dict(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,members=12,firmware_sha256=FIRMWARE,unchanged_pair_roles=8,fixture_bytes=81936,payload_bytes=81920,full_hardware_pending=True)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 (a.out/'manifest.json').write_bytes(blobs['manifest.json'])
 (a.out/'executed-release118.py').write_bytes(Path(__file__).read_bytes())
 print(json.dumps(result))
if __name__=='__main__':main()
