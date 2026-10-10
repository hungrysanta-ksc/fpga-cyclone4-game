# SPDX-License-Identifier: MIT
"""Verify frozen141 artifacts, selected source identity and package contents."""
from pathlib import Path
import argparse,csv,json,re,tempfile,shutil,hashlib,zipfile
from nes_spi_boot import ROOT,sha
from nes_cf68_pair_preflight import decode
from nes_screen141_models import prepare_models
from test_nes_screen141_core import summarize

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 meta=json.loads((ROOT/'analysis/screen141-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
 def read(n):return json.loads((e/n).read_bytes())
 fit=e/'fit';core=e/'core';arm=e/'arm';host=e/'host'
 prep=read('fit/preparation141.json')
 assert set(prep['changed'])=={'nes_rom_spi.sv','nes_run_observer134.sv','nes_rom_physical.sv','nes_rom_service.sv','rtl/nes.v'}
 for n,h in prep['copied'].items():assert sha(fit/n)==prep['changed'].get(n,h),n
 names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(fit/'board.qsf').read_text())
 with tempfile.TemporaryDirectory() as t:
  t=Path(t);(t/'rtl').mkdir()
  for n in ['nes_rom_physical.sv','rtl/nes.v']:shutil.copy2(fit/n,t/n)
  prepare_models(t)
  for n in names+['prg.hex','chr.hex','screen-program.hex']:
   assert sha(fit/n)==sha(e/'asm'/n),n
   assert (core/n).read_text()==((t/n) if n in ['nes_rom_physical.sv','rtl/nes.v'] else (fit/n)).read_text(),n
 for public_name,executed_name in [('screen141_tb.sv','screen141_tb.sv'),('screen141_boundary_tb.sv','unit141_tb.sv'),('screen141_cache_tb.sv','screen141_cache_tb.sv')]:
  assert (ROOT/'tests/nes-functional'/public_name).read_text()==(core/executed_name).read_text().replace('observerD6','observerD8'),public_name
 proof=summarize(core);assert proof==read('core/result-final.json')
 baseline=read('core/reused-control.json');assert baseline['source_differences']==['nes_rom_service.sv']
 assert sha(e/'initial/core03/core-1-3.5.log')==sha(core/'core-1-3.5.log')
 assert 'context=6702403ff400e184' in (e/'initial/core03/core-0-3.5.log').read_text()
 for c in proof['cases']:
  n=f"core-0-{c['phase_ns']}"
  # File names retain integer0, not0.0.
  if c['phase_ns']==0:n='core-0-0'
  assert sha(core/(n+'-frame-1.hex'))==meta['nominal_frame_sha256']
 reader=read('reader/result.json');assert reader['passed'] and reader['negative110_rejected'] and reader['negative_hold_rejected']
 assert len(reader['cases'])==16 and sum(x['completed'] for x in reader['cases'])==8400
 assert sha(fit/'nes_rom_physical.sv')==sha(e/'reader/nes_rom_physical.sv')
 for n in ['nes_menu_return.c','nes_menu_diagnostic.c','nes_h1_stm32.c','nes_run136.inc','nes_rom_verify.c','nes_checkpoint112.c']:
  assert sha(arm/'src'/n)==sha(host/n),n
 assert len(read('host/result.json')['cases'])==21
 for i in range(21):assert 'PASS136' in (host/f'case-{i}.log').read_text()
 assert read('budget-negative/result.json')['negative_rejected']
 assert sha(e/'budget-negative/nes_menu_return.c')==meta['old_menu_return_sha256']
 t=list(csv.DictReader((e/'inventory/timing141.tsv').read_text().splitlines(),delimiter='\t'))
 for kind in ['setup','hold']:assert min(float(x['slack']) for x in t if x['group']=='same_clock' and x['type']==kind)>0
 sta=read('sta/sta141.json');io=read('io/result.json');ac=read('armcheck/result.json')
 assert sta['passed'] and sta['chains']==17 and io['passed'] and io['conditional_read_margin_ns']>0
 assert ac['strong_nmi'] and ac['host_sources_match']
 fw=arm/'src/obj-nes-100/firmware.stm';fpga=e/'asm/fpga_n141.bi3'
 assert sha(fw)==ac['firmware_sha256'] and decode(fpga.read_bytes())==(e/'asm/output_files/board.rbf').read_bytes()
 pkg=e/'release/NES141-SCREEN-and-RESTORE044.zip';assert sha(pkg)==meta['package']['zip_sha256']
 with zipfile.ZipFile(pkg) as z:
  m=json.loads(z.read('manifest.json'));assert len(z.namelist())==12
  for n,v in m['files'].items():assert hashlib.sha256(z.read(n)).hexdigest()==v['sha256']
  assert z.read('01-SCREEN141-SD-ROOT/sd2snes/firmware.stm')==fw.read_bytes()
  assert z.read('01-SCREEN141-SD-ROOT/sd2snes/fpga_n141.bi3')==fpga.read_bytes()
  assert not z.read('01-SCREEN141-SD-ROOT/NES SCREEN 141.nh1')
  assert not json.loads(z.read('decision141.json'))['unchanged044_retest_required']
 assert not meta['physical_screen_tested'] and not meta['game_ready']
 print(json.dumps(dict(passed=True,files=len(files),host_cases=21,normal_trial_ready=True,physical=False)))

if __name__=='__main__':main()
