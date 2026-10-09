# SPDX-License-Identifier: MIT
"""Stage a review-only 80KiB trial; never authorize a trial or write an SD."""
from pathlib import Path
import argparse,json,hashlib,zipfile,shutil
from nes_pair109 import verify,MARKERS
from nes_spi_boot import ROOT

PAIR='788dca6e5546456340ef03579b91a46a0496724a899432df389d48f0c69aae69'
FILES={
 'review-only/trial/sd2snes/firmware.stm':'arm108.stm',
 'review-only/trial/sd2snes/fpga_n86.bi3':'cf86.packed',
 'review-only/trial/sd2snes/fpga_base.bi3':'base.packed',
 'review-only/trial/sd2snes/m3nu.bin':'menu.bin',
 'review-only/trial/sd2snes/nes/fine_x.nes':'fixture80.nes',
 'review-only/trial/'+MARKERS[0]:'marker0.empty',
 'review-only/restore/sd2snes/firmware.stm':'restore044.stm',
 'review-only/restore/sd2snes/fpga_base.bi3':'base.packed',
 'review-only/restore/sd2snes/m3nu.bin':'menu.bin'}
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ['pair','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();assert verify(a.pair,PAIR)['pair_identity_pass']
 a.out.mkdir(parents=True);blobs={n:(a.pair/'files'/source).read_bytes() for n,source in FILES.items()}
 decision=json.loads((ROOT/'docs/nes-trial110-decision.json').read_bytes())
 assert decision['selection']=='pending' and not decision['hardware_trial_approved'] and not decision['installable']
 for name in ['nes-trial110-decision.json','nes-trial110-review.ko.md']:blobs['review-only/'+name]=(ROOT/'docs'/name).read_bytes()
 blobs['DO-NOT-INSTALL.txt']='검토용 후보입니다. 미계측 조건을 남긴 제한 시험 선택은 아직 미확정입니다. SD에 복사하거나 실행하지 마세요.\n'.encode('utf-8')
 manifest=dict(candidate='NES-TRIAL-REVIEW-110',pair_manifest_sha256=PAIR,hardware_trial_approved=False,installable=False,files={n:dict(bytes=len(b),sha256=digest(b),source_role=FILES.get(n)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
 archive=a.out/'NES110-REVIEW-DO-NOT-INSTALL.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():z.writestr(n,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs) and len(z.namelist())==len(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
  assert not any('96.nh1' in n or 'banks32.nes' in n for n in z.namelist())
 result=dict(zip_sha256=digest(archive.read_bytes()),members=len(blobs),file_roles=len(FILES),pair_manifest_sha256=PAIR,hardware_trial_approved=False,installable=False,physical=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 (a.out/'manifest.json').write_bytes(blobs['manifest.json']);shutil.copy2(__file__,a.out/'executed-stage110.py')
 print(json.dumps(result))
if __name__=='__main__':main()
