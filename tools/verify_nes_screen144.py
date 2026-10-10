# SPDX-License-Identifier: MIT
"""Check frozen144 source, changed-ROM pair, tested packets and package identity."""
from pathlib import Path
import argparse,json,re,zipfile,hashlib
from nes_spi_boot import ROOT,sha
from nes_cf68_pair_preflight import decode

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 def read(n):return json.loads((e/n).read_bytes())
 m=json.loads((ROOT/'analysis/screen144-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 files=read('manifest.json')['files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for n,h in m['unchanged_routing_inputs'].items():assert sha(e/'fit'/n)==sha(e/'asm'/n)==h,n
 update=read('fit/rom-update144.json');assert update['mif_all_bytes_verified']==24576 and not update['new_map_fit']
 mif=e/'fit'/update['generated_mif'];assert sha(mif)==update['generated_mif_sha256']
 values={int(x):int(y,2) for x,y in re.findall(r'(\d+)\s*:\s*([01]{8});',mif.read_text())}
 assert bytes(values[i] for i in range(24576))==bytes.fromhex((e/'fit/screen-program.hex').read_text())
 assert sha(e/'fit/screen-program.hex')==sha(e/'bus/screen-program.hex')==sha(e/'asm/screen-program.hex')
 assert sha(e/'fit/client/screen144.sfc')==read('client/result.json')['inputs']['rom']==read('reference/result.json')['source_rom_sha256']
 for n in ['client','bad_length','bad_header','core','bus','status']:assert read(n+'/result.json')['passed'],n
 assert read('core/result.json')['independent_banner_pixels']==245760
 assert read('core/result.json')['banks']==[0,1,0,1]
 assert not read('status/result.json')['physical_root_cause_confirmed']
 assert len(read('host/result.json')['cases'])==21
 for n in ['nes_menu_return.c','nes_menu_diagnostic.c','nes_h1_stm32.c','nes_run136.inc','nes_checkpoint112.c','nes_run136.h','nes_rom_spi.c']:assert sha(e/'host'/n)==sha(e/'arm/src'/n),n
 fields=dict(s.split('=',1) for s in (e/'host/case-0-report.txt').read_text().splitlines());assert fields['screen_telemetry_trusted']=='0'
 assert sha(e/'reference/EXPECTED-SCREENS.png')==read('reference/result.json')['png_sha256']
 ac=read('armcheck/result.json');fw=e/'arm/src/obj-nes-100/firmware.stm';fpga=e/'asm/fpga_n144.bi3'
 assert ac['strong_nmi'] and ac['host_sources_match'] and sha(fw)==ac['firmware_sha256']
 assert decode(fpga.read_bytes())==(e/'asm/output_files/board.rbf').read_bytes()
 fixture=(e/'fixture/screen144.nes').read_bytes();assert fixture==(e/'core/fine_x/screen144.nes').read_bytes()==(e/'host/fixture.nes').read_bytes()
 pkg=e/'release/NES144-SCREEN-and-RESTORE044.zip';assert sha(pkg)==m['package']['zip_sha256']
 with zipfile.ZipFile(pkg) as z:
  assert len(z.namelist())==13
  for n,v in json.loads(z.read('manifest.json'))['files'].items():assert hashlib.sha256(z.read(n)).hexdigest()==v['sha256']
  assert z.read('01-SCREEN144-SD-ROOT/sd2snes/firmware.stm')==fw.read_bytes()
  assert z.read('01-SCREEN144-SD-ROOT/sd2snes/fpga_n144.bi3')==fpga.read_bytes()
  assert z.read('01-SCREEN144-SD-ROOT/sd2snes/nes/screen144.nes')==fixture
  assert z.read('EXPECTED-SCREENS.png')==(e/'reference/EXPECTED-SCREENS.png').read_bytes()
  d=json.loads(z.read('decision144.json'));assert d['observations']==600 and not d['screen_telemetry_trusted'] and not d['unchanged044_retest_required']
 assert not m['physical_tested']
 print(json.dumps(dict(passed=True,files=len(files),host_cases=21,actual_core_frames=4,independent_banner_pixels=245760,new_fit=False,physical=False)))
if __name__=='__main__':main()
