# SPDX-License-Identifier: MIT
"""Offline identity review of ARM108/CF86/044. No SD/install operation."""
from pathlib import Path
import argparse,hashlib,json
from nes_spi_boot import ROOT
from nes_cf68_pair_preflight import read,decode

POLICY=dict(installable=False,hardware_trial_approved=False,start_enabled=False,
 external_io_signoff=False,both_clock_halt_safe=False,
 persisted_report_proves_reset_release=False)
MARKERS=['NES VERIFY 094 80.nh1','NES VERIFY 094 96.nh1']
REPORT='/sd2snes/nes-verify-last-094.txt'
def digest(b):return hashlib.sha256(b).hexdigest()
def require(ok,message):
 if not ok:raise ValueError(message)
def expected():
 arm=json.loads((ROOT/'analysis/css108-verification.json').read_bytes())['arm']
 imgs=json.loads((ROOT/'analysis/config097-verification.json').read_bytes())['images']
 data={
 'arm108.stm':(arm['firmware_bytes'],arm['firmware_sha256'],'sd2snes/firmware.stm','diagnostic-firmware'),
 'cf86.packed':(imgs['diag.packed']['bytes'],imgs['diag.packed']['sha256'],'sd2snes/fpga_n86.bi3','diagnostic-fpga'),
 'cf86.raw':(imgs['diag.raw']['bytes'],imgs['diag.raw']['sha256'],None,'decode-reference'),
 'base.packed':(imgs['base.packed']['bytes'],imgs['base.packed']['sha256'],'sd2snes/fpga_base.bi3','base-reference'),
 'base.raw':(imgs['base.raw']['bytes'],imgs['base.raw']['sha256'],None,'legacy-decode-reference'),
 'menu.bin':(imgs['menu.bin']['bytes'],imgs['menu.bin']['sha256'],'sd2snes/m3nu.bin','menu-reference'),
 'fixture80.nes':(81936,'3daf26c8e2d0002c288efdf2ff694cdc14f0266b9cb32bb3efda8b9bf5d173df','sd2snes/nes/fine_x.nes','synthetic-test'),
 'fixture96.nes':(98320,'22427da4f719a0bce2b4d8417b35a45a347e76dbcab2cbc22427ace29aa1279b','sd2snes/nes/banks32.nes','synthetic-test'),
 'restore044.stm':(169056,'1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b','sd2snes/firmware.stm','manual-restore-only')}
 for i,n in enumerate(MARKERS):data[f'marker{i}.empty']=(0,digest(b''),n,'manual-selection-marker')
 return {n:dict(bytes=z,sha256=h,sd_target=t,role=r) for n,(z,h,t,r) in data.items()}
def manifest():return dict(candidate='NES-PAIR-109',firmware_version='CF86-CSS108',fpga_id_hex='86',marker_report_generation='094',report_path=REPORT,policy=POLICY.copy(),files=expected())
def verify(root,manifest_sha):
 raw=read(root,'manifest.json');require(digest(raw)==manifest_sha,'manifest digest differs')
 m=json.loads(raw);require(m==manifest(),'identity/role/policy differs from reviewed pair')
 actual={p.relative_to(Path(root)/'files').as_posix() for p in (Path(root)/'files').rglob('*') if p.is_file()}
 require(actual==set(m['files']),'unexpected or missing review files')
 blobs={n:read(root,'files/'+n) for n in m['files']}
 for n,b in blobs.items():require(len(b)==m['files'][n]['bytes'] and digest(b)==m['files'][n]['sha256'],'file mismatch: '+n)
 require(decode(blobs['cf86.packed'])==blobs['cf86.raw'],'CF86 decode mismatch')
 # Received legacy base has a different EOF-padding contract. Its actual-C
 # decode was verified in097; do not silently re-encode with the071 decoder.
 for n,prg,chr_ in [('fixture80.nes',4,2),('fixture96.nes',4,4)]:
  b=blobs[n];require(b[:4]==b'NES\x1a' and b[4]==prg and b[5]==chr_,'fixture geometry differs')
 return dict(pair_identity_pass=True,files=len(blobs),cf86_decoded_bytes=len(blobs['cf86.raw']),legacy_base_decode='reused097-actual-C',policy=POLICY.copy())
def main():
 p=argparse.ArgumentParser();p.add_argument('--review',type=Path,required=True);p.add_argument('--manifest-sha256',required=True);a=p.parse_args()
 print(json.dumps(verify(a.review,a.manifest_sha256),indent=2))
if __name__=='__main__':main()
