# SPDX-License-Identifier: MIT
"""One bounded screen experiment plus exactly the user-tested044 restore."""
from pathlib import Path
import argparse,json,zipfile,hashlib,shutil
from nes_spi_boot import ROOT,sha
from nes_cf68_pair_preflight import decode
from nes_screen144 import fixture
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','arm','arm-check','asm','host','rtl','io','reference','core','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists()
 arm=json.loads((a.arm_check/'result.json').read_bytes());asm=json.loads((a.asm/'result.json').read_bytes())
 assert json.loads((a.core/'result.json').read_bytes())['independent_banner_pixels']==245760
 assert (a.core/'fine_x/screen144.nes').read_bytes()==fixture(a.baseline)
 assert arm['strong_nmi'] and arm['host_sources_match']
 assert len(json.loads((a.host/'result.json').read_bytes())['cases'])==21
 assert json.loads((a.rtl/'result.json').read_bytes())['passed'] and json.loads((a.io/'result.json').read_bytes())['passed']
 fw=a.arm/'src/obj-nes-100/firmware.stm';fpga=a.asm/'fpga_n144.bi3'
 assert sha(fw)==arm['firmware_sha256'] and sha(fpga)==asm['packed_sha256']
 assert decode(fpga.read_bytes())==(a.asm/'output_files/board.rbf').read_bytes()
 meta=json.loads((ROOT/'analysis/run136-verification.json').read_bytes())
 old=a.baseline/'nes-run136/evidence/release01/NES136-MINIMUM-RUN-and-RESTORE044.zip'
 assert sha(old)==meta['package']['zip_sha256']
 blobs={}
 with zipfile.ZipFile(old) as z:
  m=json.loads(z.read('manifest.json'))
  for n in ['01-RUN136-SD-ROOT/sd2snes/fpga_base.bi3','01-RUN136-SD-ROOT/sd2snes/m3nu.bin','02-RESTORE044-SD-ROOT/sd2snes/firmware.stm','02-RESTORE044-SD-ROOT/sd2snes/fpga_base.bi3','02-RESTORE044-SD-ROOT/sd2snes/m3nu.bin']:
   b=z.read(n);assert digest(b)==m['files'][n]['sha256'];blobs[n.replace('01-RUN136','01-SCREEN144')]=b
 blobs['01-SCREEN144-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes()
 blobs['01-SCREEN144-SD-ROOT/sd2snes/fpga_n144.bi3']=fpga.read_bytes()
 blobs['01-SCREEN144-SD-ROOT/sd2snes/nes/screen144.nes']=fixture(a.baseline)
 blobs['01-SCREEN144-SD-ROOT/NES SCREEN 144.nh1']=b''
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-screen144-instructions.ko.md').read_bytes()
 reference=json.loads((a.reference/'result.json').read_bytes())
 assert reference['source_rom_sha256']==sha(a.asm/'client/screen144.sfc')
 assert reference['png_sha256']==sha(a.reference/'EXPECTED-SCREENS.png')
 blobs['EXPECTED-SCREENS.png']=(a.reference/'EXPECTED-SCREENS.png').read_bytes()
 decision=dict(package='NES-SCREEN-144',firmware_version='NES-SCREEN144',loader_id='5E',observer_id='D9',screen_status_command='73',screen_status_schema=1,fpga_logic_reused_from142=True,screen_frame_counter_is_software_only=True,screen_telemetry_trusted=False,visual_oracle='NES 144 and alternating A/B banners, repeated vertically',first_fault_context_schema=1,early_stop_on_observed_fault=True,marker='NES SCREEN 144.nh1',progress='/sd2snes/nes-progress-144.txt',report='/sd2snes/nes-screen-last-144.txt',normal_hardware_trial=True,unchanged044_retest_required=False,physical_screen='pending',game_ready=False,input=False,audio=False,nominal_display_wait_ms=30000,observations=600,human_observation_limit_seconds=600,full_io_signoff=False,board_delay_measured=False,both_clock_halt_safe=False,source_lock_holds=4)
 blobs['decision144.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package=decision['package'],restore_from136_zip_sha256=sha(old),files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();assert len(blobs)==13
 o.mkdir(parents=True);archive=o/'NES144-SCREEN-and-RESTORE044.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,10,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 result=dict(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,members=len(blobs),firmware_sha256=sha(fw),fpga_sha256=sha(fpga),fixture_sha256=digest(fixture(a.baseline)),normal_trial_ready=True,physical=False)
 for n in ['manifest.json','decision144.json','START-HERE.ko.md']:(o/n).write_bytes(blobs[n])
 (o/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');shutil.copy2(__file__,o/'executed-release144.py');print(json.dumps(result))
if __name__=='__main__':main()
