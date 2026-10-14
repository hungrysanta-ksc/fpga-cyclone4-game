# SPDX-License-Identifier: MIT
"""Package169 only after actualSNES/frame, ARM and ROM-update checks pass."""
from pathlib import Path
import argparse,json,hashlib,zipfile
from nes_game147 import ROOT,sha
from nes_cf68_pair_preflight import decode
def main():
 p=argparse.ArgumentParser()
 for n in ['prior','arm','arm-check','test','report','fpga','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 assert sha(a.prior)=='77de2a081e33d3d0c22e3201de22cd362ca55475694223f23b1684bb167f737c'
 ar=json.loads((a.arm_check/'result.json').read_bytes());t=json.loads((a.test/'result.json').read_bytes());report=json.loads((a.report/'result.json').read_bytes());fp=json.loads((a.fpga/'result169.json').read_bytes())
 assert all(q['passed'] for q in [ar,t,report,fp]) and ar['remaining_margin']>=1024
 assert sha(a.arm/'src/nes_menu_diagnostic.c')==report['source_sha256']
 for q in [ar,t,fp]:
  for n,h in q['public_sources'].items():assert sha(ROOT/n)==h,n
 prep=json.loads((a.arm/'preparation-banked169.json').read_bytes())
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(a.arm/n)==h,n
 assert (a.test/'client/sink-program.hex').read_bytes()==(a.fpga/'sink-program.hex').read_bytes()
 fw=a.arm/'src/obj-nes-100/firmware.stm';assert sha(fw)==ar['firmware_sha256']
 for n in ['nes_native_sink165.c','nes_sink_trace168.c']:
  assert (a.arm/'src'/n).read_bytes().replace(b'\r\n',b'\n')==(a.test/n).read_bytes().replace(b'\r\n',b'\n'),n
 packed=(a.fpga/'fpga_n169.bi3').read_bytes();assert hashlib.sha256(packed).hexdigest()==fp['fpga_sha256'] and hashlib.sha256(decode(packed)).hexdigest()==fp['rbf_sha256']
 digest=lambda b:hashlib.sha256(b).hexdigest();blobs={};preserved={}
 with zipfile.ZipFile(a.prior) as z:
  prior=json.loads(z.read('manifest.json'))
  for n,v in prior['files'].items():
   b=z.read(n);assert len(b)==v['bytes'] and digest(b)==v['sha256']
   if n.startswith(('01-GAME168-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('168','169') if n.startswith('01-') else n;blobs[dst]=b
    if dst not in ['01-GAME169-SD-ROOT/sd2snes/firmware.stm','01-GAME169-SD-ROOT/sd2snes/fpga_n169.bi3']:preserved[dst]=digest(b)
 blobs['01-GAME169-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes();blobs['01-GAME169-SD-ROOT/sd2snes/fpga_n169.bi3']=packed
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game169-ready.ko.md').read_bytes()
 decision=dict(trial_ready=True,physical=False,fps_approved=False,method='small diffs plus inactive VRAM full update on E2/E3; final vblank flip',run_ticks=6000,run_sd_writes=False,save_sram_used=False,stack_margin=ar['remaining_margin'],new_map_fit=False)
 blobs['decision169.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES169-SMB3-BANKED-VIDEO',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 archive=a.out/'NES169-SMB3-BANKED-VIDEO.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,13,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b
 for n,h in preserved.items():assert digest(blobs[n])==h
 for n in ['START-HERE.ko.md','manifest.json','decision169.json']:(a.out/n).write_bytes(blobs[n])
 r=dict(passed=True,zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,firmware_sha256=sha(fw),fpga_sha256=digest(packed),preserved=preserved,physical=False,public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_banked169.py','docs/nes-game169-ready.ko.md']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS169 PACKAGE',sha(archive))
if __name__=='__main__':main()
