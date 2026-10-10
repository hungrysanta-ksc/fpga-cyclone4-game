# SPDX-License-Identifier: MIT
"""Read-only138 evidence, final pair, and reused137 functional boundary audit."""
from pathlib import Path
import argparse,csv,json,re,hashlib,zipfile
from nes_spi_boot import ROOT,sha
from nes_cf68_pair_preflight import decode
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 meta=json.loads((ROOT/'analysis/display138-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
 def read(n):return json.loads((e/n).read_bytes())
 fit=e/'fit01';prep=read('fit01/preparation138.json')
 assert set(prep['changed'])=={'nes_rom_spi.sv','nes_run_observer134.sv'}
 for n,h in prep['copied'].items():assert sha(fit/n)==prep['changed'].get(n,h),n
 names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(fit/'board.qsf').read_text())
 for n in names+['board.qsf','board.sdc','screen-program.hex']:
  assert sha(fit/n)==sha(e/'rtl01'/n)==sha(e/'asm01'/n),n
 arm=e/'arm02';host=e/'host07'
 for n in ['nes_menu_diagnostic.c','nes_h1_stm32.c','nes_checkpoint112.c','nes_run136.inc','nes_run136.h','nes_rom_verify.c','nes_rom_spi.c','nes_cf86_session094.c','nes_cf86_session094.h']:
  assert sha(arm/'src'/n)==sha(host/n),n
 assert len(read('host07/result.json')['cases'])==16 and read('rtl01/result.json')['passed']
 for i in range(16):assert 'PASS136' in (host/f'case-{i}.log').read_text()
 for i in [0,2,3,6]:assert 'PASS109' in (host/f'case-{i}.log').read_text()
 t=list(csv.DictReader((e/'inventory01/timing138.tsv').read_text().splitlines(),delimiter='\t'))
 for kind in ['setup','hold']:
  xs=[x for x in t if x['group']=='same_clock' and x['type']==kind]
  assert len(xs)==12 and min(float(x['slack']) for x in xs)>0
 sta=read('sta01/sta138.json');io=read('io01/result.json');ac=read('armcheck01/result.json')
 assert sta['constrained_pairs']==363 and sta['chains']==17 and sta['passed']
 assert io['passed'] and io['negative_only_release_async_inputs'] and io['conditional_read_margin_ns']>0
 assert ac['strong_nmi'] and ac['host_sources_match']
 fw=arm/'src/obj-nes-100/firmware.stm';fpga=e/'asm01/fpga_n138.bi3'
 assert sha(fw)==ac['firmware_sha256']
 assert decode(fpga.read_bytes())==(e/'asm01/output_files/board.rbf').read_bytes()
 pkg=e/'release01/NES138-SCREEN-and-RESTORE044.zip';assert sha(pkg)==meta['package']['zip_sha256']
 with zipfile.ZipFile(pkg) as z:
  m=json.loads(z.read('manifest.json'));assert len(z.namelist())==12
  for n,v in m['files'].items():assert hashlib.sha256(z.read(n)).hexdigest()==v['sha256']
  assert z.read('01-SCREEN138-SD-ROOT/sd2snes/firmware.stm')==fw.read_bytes()
  assert z.read('01-SCREEN138-SD-ROOT/sd2snes/fpga_n138.bi3')==fpga.read_bytes()
  assert z.read('01-SCREEN138-SD-ROOT/sd2snes/nes/screen138.nes')==(fit/'screen138.nes').read_bytes()
  assert not z.read('01-SCREEN138-SD-ROOT/NES SCREEN 138.nh1')
 assert not meta['physical_screen_tested'] and not meta['game_ready']
 print(json.dumps(dict(passed=True,files=len(files),host_cases=16,normal_trial_ready=True,physical_screen_tested=False)))
if __name__=='__main__':main()
