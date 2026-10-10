# SPDX-License-Identifier: MIT
"""Verify frozen142 identities, tested ROM bytes, firmware and delivery ZIP."""
from pathlib import Path
import argparse,json,re,hashlib,zipfile
from nes_spi_boot import ROOT,sha
from nes_cf68_pair_preflight import decode

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 meta=json.loads((ROOT/'analysis/screen142-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
 def read(n):return json.loads((e/n).read_bytes())
 fit=e/'fit';asm=e/'asm';rom=fit/'client/screen142.sfc'
 names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(fit/'board.qsf').read_text())
 for n in names+['screen-program.hex','prg.hex','chr.hex','board.qsf','board.sdc']:assert sha(fit/n)==sha(asm/n),n
 for n in ['nes_screen_status142.sv','nes_screen_bus137.sv','screen-program.hex']:assert sha(fit/n)==sha(e/'status'/n),n
 assert sha(fit/'nes_screen_status142.sv')==sha(ROOT/'src/nes/diagnostic/nes_screen_status142.sv')
 update=read('fit/rom-update142.json');assert update['mif_all_bytes_verified']==24576
 mif=fit/update['generated_mif'];assert sha(mif)==update['generated_mif_sha256']
 values={int(x):int(y,2) for x,y in re.findall(r'(\d+)\s*:\s*([01]{8});',mif.read_text())}
 assert set(values)==set(range(24576))
 assert bytes(values[i] for i in range(24576))==bytes.fromhex((fit/'screen-program.hex').read_text())
 assert sha(rom)==read('client/result.json')['inputs']['rom']==update['client_sha256']
 for n in ['client','client-bad-length','client-bad-header','status','reply','inputs','io']:assert read(n+'/result.json')['passed'],n
 assert 'PASS142 STATUS checks=40' in (e/'status/status.log').read_text()
 assert read('reply/result.json')['cases']==8 and read('status/result.json')['rom_bytes']==65536
 assert len(read('host/result.json')['cases'])==21
 for n in ['nes_menu_return.c','nes_menu_diagnostic.c','nes_h1_stm32.c','nes_run136.inc','nes_rom_verify.c','nes_checkpoint112.c']:assert sha(e/'arm/src'/n)==sha(e/'host'/n),n
 for n,h in meta['unchanged_core_sources'].items():assert sha(fit/n)==h,n
 ac=read('armcheck/result.json');assert ac['host_sources_match'] and ac['strong_nmi']
 fw=e/'arm/src/obj-nes-100/firmware.stm';fpga=asm/'fpga_n142.bi3'
 assert sha(fw)==ac['firmware_sha256'] and decode(fpga.read_bytes())==(asm/'output_files/board.rbf').read_bytes()
 pkg=e/'release/NES142-SCREEN-and-RESTORE044.zip';assert sha(pkg)==meta['package']['zip_sha256']
 with zipfile.ZipFile(pkg) as z:
  m=json.loads(z.read('manifest.json'));assert len(z.namelist())==12
  for n,v in m['files'].items():assert hashlib.sha256(z.read(n)).hexdigest()==v['sha256']
  assert z.read('01-SCREEN142-SD-ROOT/sd2snes/firmware.stm')==fw.read_bytes()
  assert z.read('01-SCREEN142-SD-ROOT/sd2snes/fpga_n142.bi3')==fpga.read_bytes()
  d=json.loads(z.read('decision142.json'));assert (d['loader_id'],d['observer_id'])==('5E','D9')
  assert not d['unchanged044_retest_required'] and not z.read('01-SCREEN142-SD-ROOT/NES SCREEN 142.nh1')
 assert not meta['physical_screen_tested'] and not meta['game_ready']
 print(json.dumps(dict(passed=True,files=len(files),host_cases=21,status_checks=40,normal_trial_ready=True,physical=False)))
if __name__=='__main__':main()
