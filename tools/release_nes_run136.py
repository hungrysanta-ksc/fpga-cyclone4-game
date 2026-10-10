# SPDX-License-Identifier: MIT
"""Bundle the checked136 MCU/135 FPGA and known044 restore for one normal trial."""
from pathlib import Path
import argparse,json,zipfile,shutil
from nes_spi_boot import ROOT,sha
from nes_pair109 import verify,digest
from stage_nes_trial110 import PAIR
from nes_cf68_pair_preflight import decode
from nes_run136_mcu import fixture

def main():
 p=argparse.ArgumentParser()
 for n in ['pair','arm','arm-check','asm','host','rtl','io','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists();assert verify(a.pair,PAIR)['pair_identity_pass']
 arm=json.loads((a.arm_check/'result.json').read_bytes());asm=json.loads((a.asm/'result.json').read_bytes())
 assert arm['strong_nmi'] and arm['host_sources_match']
 assert len(json.loads((a.host/'result.json').read_bytes())['cases'])==8
 assert json.loads((a.rtl/'result.json').read_bytes())['passed']
 assert json.loads((a.io/'result.json').read_bytes())['passed']
 fw=a.arm/'src/obj-nes-100/firmware.stm';fpga=a.asm/'fpga_n136.bi3'
 assert sha(fw)==arm['firmware_sha256'] and sha(fpga)==asm['packed_sha256']
 assert decode(fpga.read_bytes())==(a.asm/'output_files/board.rbf').read_bytes()
 blobs={};roles={}
 for name,role in [('01-RUN136-SD-ROOT/sd2snes/fpga_base.bi3','base.packed'),('01-RUN136-SD-ROOT/sd2snes/m3nu.bin','menu.bin'),('02-RESTORE044-SD-ROOT/sd2snes/firmware.stm','restore044.stm'),('02-RESTORE044-SD-ROOT/sd2snes/fpga_base.bi3','base.packed'),('02-RESTORE044-SD-ROOT/sd2snes/m3nu.bin','menu.bin')]:
  blobs[name]=(a.pair/'files'/role).read_bytes();roles[name]=role
 blobs['01-RUN136-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes()
 blobs['01-RUN136-SD-ROOT/sd2snes/fpga_n136.bi3']=fpga.read_bytes()
 blobs['01-RUN136-SD-ROOT/sd2snes/nes/run136.nes']=fixture()
 blobs['01-RUN136-SD-ROOT/NES RUN 136.nh1']=b''
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-run136-instructions.ko.md').read_bytes()
 decision=dict(package='NES-MINIMUM-RUN-136',firmware_version='NES-RUN136',selected_fit='135fit03',loader_id='59',observer_id='D4',marker='NES RUN 136.nh1',progress='/sd2snes/nes-progress-136.txt',report='/sd2snes/nes-run-last-136.txt',scope='synthetic80 full load/CHECK, bounded16 observations, RUN STOP retaining image, base/menu and044 restore',normal_hardware_trial=True,start_enabled=True,physical_result='pending',full_game_installable=False,full_io_signoff=False,both_clock_halt_safe=False,common_cause_8us_proven=False,source_lock_holds_unchanged=4,human_observation_limit_seconds=600,nominal_run_wait_ms=16,run_observations=16)
 blobs['decision136.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package=decision['package'],restore_pair_manifest=PAIR,files={n:dict(bytes=len(b),sha256=digest(b),role=roles.get(n)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();assert len(blobs)==12
 o.mkdir(parents=True);archive=o/'NES136-MINIMUM-RUN-and-RESTORE044.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,10,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert len(z.namelist())==len(blobs) and set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 result=dict(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,members=12,firmware_bytes=fw.stat().st_size,firmware_sha256=sha(fw),fpga_bytes=fpga.stat().st_size,fpga_sha256=sha(fpga),fixture_sha256=digest(fixture()),fixture_bytes=len(fixture()),physical=False,normal_trial_ready=True)
 (o/'manifest.json').write_bytes(blobs['manifest.json']);(o/'decision136.json').write_bytes(blobs['decision136.json']);(o/'START-HERE.ko.md').write_bytes(blobs['START-HERE.ko.md'])
 (o/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');shutil.copy2(__file__,o/'executed-release136.py');print(json.dumps(result))
if __name__=='__main__':main()
