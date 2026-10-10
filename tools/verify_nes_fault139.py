# SPDX-License-Identifier: MIT
"""Read-only verification of frozen139 evidence and the exact hardware pair."""
from pathlib import Path
import argparse,csv,json,re,hashlib,zipfile
from nes_spi_boot import ROOT,sha
from nes_cf68_pair_preflight import decode
from read_nes_fault139 import decode as decode_context
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 meta=json.loads((ROOT/'analysis/fault139-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
 def read(n):return json.loads((e/n).read_bytes())
 fit=e/'fit02';prep=read('fit02/preparation139.json')
 assert set(prep['changed'])=={'nes_rom_spi.sv','nes_rom_service.sv','nes_live_joint.sv','fxpak_nes_screen137_top.sv','nes_run_observer134.sv'}
 for n,h in prep['copied'].items():assert sha(fit/n)==prep['changed'].get(n,h),n
 # Remove only observation ports/assignments; original service body must match138.
 s=(fit/'nes_rom_service.sv').read_text()
 s=s.replace('output wire fault_trigger,output wire [63:0] fault_context,\n ','')
 start=s.index(' //139 Parallel observation only.');end=s.index(' always @(posedge clk or posedge reset)begin',start)
 s=s[:start]+s[end:]
 assert hashlib.sha256(s.encode()).hexdigest()==prep['copied']['nes_rom_service.sv']
 names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(fit/'board.qsf').read_text())
 for n in names+['board.qsf','board.sdc','screen-program.hex']:
  assert sha(fit/n)==sha(e/'rtl01'/n)==sha(e/'asm01'/n),n
 arm=e/'arm03';host=e/'host05'
 for n in ['nes_menu_diagnostic.c','nes_h1_stm32.c','nes_checkpoint112.c','nes_run136.inc','nes_run136.h','nes_rom_verify.c','nes_rom_spi.c','nes_cf86_session094.c','nes_cf86_session094.h']:
  assert sha(arm/'src'/n)==sha(host/n),n
 assert sha(arm/'src/nes_run136.inc')==sha(ROOT/'src/nes/firmware/nes_fault139.inc')
 assert len(read('host05/result.json')['cases'])==20 and read('rtl01/result.json')['passed']
 for i in range(20):assert 'PASS136' in (host/f'case-{i}.log').read_text()
 for i in [3,19]:
  report=decode_context((host/f'case-{i}-report.txt').read_text());assert report['cpu_address']=='0x0008123' and report['pending_address']=='0x200456' and report['age_nes_clocks']==7
  assert report['first_run_error']==1 and report['stop_error']==(3 if i==19 else 0)
 t=list(csv.DictReader((e/'inventory01/timing139.tsv').read_text().splitlines(),delimiter='\t'))
 for kind in ['setup','hold']:
  xs=[x for x in t if x['group']=='same_clock' and x['type']==kind];assert len(xs)==12 and min(float(x['slack']) for x in xs)>0
 sta=read('sta01/sta139.json');io=read('io01/result.json');ac=read('armcheck03/result.json')
 assert sta['constrained_pairs']==363 and sta['chains']==17 and sta['passed']
 assert io['passed'] and io['negative_only_release_async_inputs'] and io['conditional_read_margin_ns']>0
 assert ac['strong_nmi'] and ac['host_sources_match']
 fw=arm/'src/obj-nes-100/firmware.stm';fpga=e/'asm01/fpga_n139.bi3'
 assert sha(fw)==ac['firmware_sha256']
 assert decode(fpga.read_bytes())==(e/'asm01/output_files/board.rbf').read_bytes()
 pkg=e/'release01/NES139-SCREEN-and-RESTORE044.zip';assert sha(pkg)==meta['package']['zip_sha256']
 with zipfile.ZipFile(pkg) as z:
  m=json.loads(z.read('manifest.json'));assert len(z.namelist())==12
  for n,v in m['files'].items():assert hashlib.sha256(z.read(n)).hexdigest()==v['sha256']
  assert z.read('01-SCREEN139-SD-ROOT/sd2snes/firmware.stm')==fw.read_bytes()
  assert z.read('01-SCREEN139-SD-ROOT/sd2snes/fpga_n139.bi3')==fpga.read_bytes()
  fixture=z.read('01-SCREEN139-SD-ROOT/sd2snes/nes/screen139.nes')
  assert hashlib.sha256(fixture).hexdigest()=='3daf26c8e2d0002c288efdf2ff694cdc14f0266b9cb32bb3efda8b9bf5d173df'
  assert not z.read('01-SCREEN139-SD-ROOT/NES SCREEN 139.nh1')
 assert not meta['physical_screen_tested'] and not meta['game_ready']
 print(json.dumps(dict(passed=True,files=len(files),host_cases=20,normal_trial_ready=True,physical_screen_tested=False)))
if __name__=='__main__':main()
