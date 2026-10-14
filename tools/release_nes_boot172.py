# SPDX-License-Identifier: MIT
"""Package the exact tested172 MCU/ROM with unchanged171 routed FPGA."""
from pathlib import Path
import argparse,json,zipfile,hashlib
from nes_game147 import ROOT,sha
from nes_cf68_pair_preflight import decode
def main():
 p=argparse.ArgumentParser()
 for n in ['prior','arm','arm-check','fpga','client','boot-test','gate-test','display-test','report','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 load=lambda p:json.loads(p.read_bytes())
 ar=load(a.arm_check/'result.json');fp=load(a.fpga/'result172.json');bt=load(a.boot_test/'result.json');gt=load(a.gate_test/'result.json');dt=load(a.display_test/'result.json');rp=load(a.report/'result.json')
 assert all(x['passed'] for x in [ar,fp,bt,gt,dt,rp]) and ar['remaining_margin']>=1024
 assert bt['client_sha256']==fp['client_sha256']==sha(a.client/'sink-program.hex')==sha(a.display_test/'client/sink-program.hex')
 assert gt['gate_sha256']==sha(a.arm/'src/nes_boot172.inc')==sha(ROOT/'src/nes/firmware/nes_boot172.inc')
 assert rp['source_sha256']==sha(a.arm/'src/nes_menu_diagnostic.c')
 for q in [ar,fp,bt,dt]:
  for n,h in q['public_sources'].items():assert sha(ROOT/n)==h,n
 prep=load(a.arm/'preparation-boot172.json')
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(a.arm/n)==h,n
 fw=a.arm/'src/obj-nes-100/firmware.stm';bit=a.fpga/'fpga_n172.bi3';assert sha(fw)==ar['firmware_sha256'] and sha(bit)==fp['fpga_sha256']
 assert decode(bit.read_bytes())==(a.fpga/'output_files/board.rbf').read_bytes()
 assert sha(a.prior)=='4782ef2f75f8f90cbcc30510bde821b5d3efda27846146b9209962652ba92b03'
 blobs={};preserved={};digest=lambda b:hashlib.sha256(b).hexdigest()
 with zipfile.ZipFile(a.prior) as z:
  for n,q in json.loads(z.read('manifest.json'))['files'].items():
   b=z.read(n);assert digest(b)==q['sha256'] and len(b)==q['bytes']
   if n.startswith(('01-GAME171-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('171','172') if n.startswith('01-') else n;blobs[dst]=b
    if dst not in ['01-GAME172-SD-ROOT/sd2snes/firmware.stm','01-GAME172-SD-ROOT/sd2snes/fpga_n172.bi3']:preserved[dst]=digest(b)
 blobs['01-GAME172-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes();blobs['01-GAME172-SD-ROOT/sd2snes/fpga_n172.bi3']=bit.read_bytes()
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game172-ready.ko.md').read_bytes()
 decision=dict(trial_ready=True,physical=False,root_cause_fixed=False,continuous_video_proven=False,run_ticks_after_ready=6000,boot_wait_ticks=500,boot_poll_cap=65536,run_sd_writes=False,save_sram_used=False,remaining_margin=ar['remaining_margin'],fpga_logic_routing='unchanged171',snes_rom='172 copy verification and ready stages')
 blobs['decision172.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest={'package':'NES172-SMB3-BOOT-READY','files':{n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()}}
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 archive=a.out/'NES172-SMB3-BOOT-READY.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,14,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b
 assert all(digest(blobs[n])==h for n,h in preserved.items())
 result=dict(passed=True,zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,firmware_sha256=sha(fw),fpga_sha256=sha(bit),preserved=preserved,decision=decision)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
