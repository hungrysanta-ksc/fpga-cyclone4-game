# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,zipfile,shutil
from nes_spi_boot import ROOT,sha
from nes_pair109 import verify,digest
from stage_nes_trial110 import FILES,PAIR

FIRMWARE='ac778c02d7561f2813c0930a8fecd3af67b4ca886455a214b068a3fbbb40fb16'
def main():
 p=argparse.ArgumentParser()
 for n in ['pair','firmware','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();assert verify(a.pair,PAIR)['pair_identity_pass']
 assert sha(a.firmware)==FIRMWARE and a.firmware.stat().st_size==184452
 roles={n.replace('review-only/trial/','01-TRIAL-SD-ROOT/').replace('review-only/restore/','02-RESTORE044-SD-ROOT/'):role for n,role in FILES.items()}
 blobs={n:(a.firmware if role=='arm108.stm' else a.pair/'files'/role).read_bytes() for n,role in roles.items()}
 roles['01-TRIAL-SD-ROOT/sd2snes/firmware.stm']='arm112.stm'
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-checkpoint112-instructions.ko.md').read_bytes()
 decision=dict(candidate='NES-CHECKPOINT-112',authorization='direct user request to build improved phase-log firmware; same approved normal80KiB single trial',firmware_version='CF86-LOG112',hardware_trial_approved=True,full_nes_installable=False,start_enabled=False,electrical_signoff=False,common_cause_8us_proven=False,physical_result='pending',attempts=1,fixture_kib=80,human_limit_seconds=600)
 blobs['decision112.json']=(json.dumps(decision,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
 m=dict(candidate='NES-CHECKPOINT-112',unchanged_pair_reference=PAIR,files={n:dict(bytes=len(b),sha256=digest(b),role=roles.get(n)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(m,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
 a.out.mkdir(parents=True);zpath=a.out/'NES112-PROGRESS-LOG-and-RESTORE044.zip'
 with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,9,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(zpath) as z:
  assert len(z.namelist())==12 and set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 result=dict(zip_sha256=sha(zpath),zip_bytes=zpath.stat().st_size,members=12,firmware_sha256=FIRMWARE,firmware_bytes=184452,unchanged_roles=8,new_fpga=False,physical=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');(a.out/'manifest.json').write_bytes(blobs['manifest.json']);shutil.copy2(__file__,a.out/'executed-release112.py');print(json.dumps(result))
if __name__=='__main__':main()
