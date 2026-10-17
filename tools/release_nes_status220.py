# SPDX-License-Identifier: MIT
"""Package220 only after functional, fitted-board, ARM and actual ROM atom gates."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from nes_runtime213 import ROOT,BASE,sha
def read(p):return json.loads(p.read_bytes())
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
 d=BASE/'probes/nes-status220';arm=d/'arm01';prep=read(arm/'preparation-status220.json')
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(arm/n)==h,n
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 assert prep['runtime_unchanged215'] and set(prep['changed'])=={'src/VERSION','src/nes_checkpoint112.c','src/nes_menu_diagnostic.c'}
 evidence=read(d/'evidence03/result.json');board=evidence['board'];check=read(d/'check01/result.json');asm=read(d/'asm01/result220.json');rom=read(d/'romcheck01/result.json')
 assert evidence['functional_pass'] and board['related_timing_passed'] and board['io']['conditional_data_bounds_pass'] and board['io']['native_payload_reset_pass']
 assert check['passed'] and check['remaining_margin']==4952 and asm['passed'] and not asm['new_fit'] and rom['passed']
 assert len(rom['checks'])==3 and all(x['matched_bytes']==4096 for x in rom['checks'])
 assert asm['client_sha256']==rom['expected_hex_sha256']==sha(BASE/'probes/nes-runtime213/asm01/sink-program.hex')
 for report in [evidence,check,asm,rom]:
  for n,h in report['public_sources'].items():assert sha(ROOT/n)==h,n
 for n,h in asm['baseline_pins'].items():assert sha(d/'mapfit02'/n)==h,n
 for n,h in asm['unchanged_routing_and_sources'].items():
  if n=='board.qsf' and sha(d/'asm01'/n)!=h:
   before=(d/'mapfit02'/n).read_text().replace('LAST_QUARTUS_VERSION "25.1std.0 Lite Edition"','LAST_QUARTUS_VERSION "25.1std.0 Standard Edition"').splitlines()
   eda=['','set_global_assignment -name EDA_SIMULATION_TOOL "QuestaSim (Verilog)"','set_global_assignment -name EDA_NETLIST_WRITER_OUTPUT_DIR simulation/modelsim -section_id eda_simulation','set_global_assignment -name EDA_OUTPUT_DATA_FORMAT "VERILOG HDL" -section_id eda_simulation']
   assert (d/'asm01'/n).read_text().splitlines()==before+eda,n
  else:assert sha(d/'asm01'/n)==h,n
 for item in rom['checks']:assert sha(d/'asm01/simulation/modelsim'/item['file'])==item['netlist_sha256']
 old=BASE/'probes/nes-plan215/release01';oldr=read(old/'result.json');oldz=old/'NES215-SMB3-PLAN-CAUSE.zip';assert sha(oldz)==oldr['zip_sha256']
 blobs={};preserved={};changed={'01-GAME220-SD-ROOT/sd2snes/firmware.stm','01-GAME220-SD-ROOT/sd2snes/fpga_n220.bi3'}
 with zipfile.ZipFile(oldz) as z:
  for n,item in read(old/'manifest.json')['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256']
   if n.startswith(('01-GAME215-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('215','220') if n.startswith('01-') else n;blobs[dst]=b
    if dst not in changed:preserved[dst]=digest(b)
 fw=(arm/'src/obj-nes-100/firmware.stm').read_bytes();fpga=(d/'asm01/fpga_n220.bi3').read_bytes()
 assert digest(fw)==check['firmware_sha256'] and sha(arm/'src/obj-nes-100/sd2snes.elf')==check['elf_sha256']
 assert digest(fpga)==asm['fpga_sha256']
 for marker in [b'NES GAME 220.nh1',b'game220.nes',b'fpga_n220.bi3',b'nes-progress-220.txt',b'nes-game-last-220.txt',b'nes-budget-220.txt',b'plan_reply_hex=',b'boot_reason=']:assert marker in fw,marker
 blobs['01-GAME220-SD-ROOT/sd2snes/firmware.stm']=fw;blobs['01-GAME220-SD-ROOT/sd2snes/fpga_n220.bi3']=fpga
 decision=dict(trial_ready=True,physical=False,physical_root_cause_fixed=False,measured_fps=None,new_fit=True,new_asm=True,current212_snes_rom=True,normal_wait_fix216=True,runtime_unchanged215=True,remaining_margin=4952,run_ticks=6000,save_sram_unchanged=True,gbc164_unchanged=True)
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game220-ready.ko.md').read_bytes();blobs['decision220.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES220-SMB3-WAIT-FIX',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()});blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 zout=a.out/'NES220-SMB3-WAIT-FIX.zip'
 with zipfile.ZipFile(zout,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   i=zipfile.ZipInfo(n,(2026,10,17,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
 with zipfile.ZipFile(zout) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 r=dict(passed=True,decision=decision,zip_sha256=sha(zout),firmware_sha256=digest(fw),fpga_sha256=digest(fpga),preserved=preserved,prior215_zip_sha256=sha(oldz),
  gates={n:sha(d/n/'result.json') for n in ['evidence03','check01','romcheck01']}|{'asm01':sha(d/'asm01/result220.json')},
  public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_status220.py','docs/nes-game220-ready.ko.md']},
  arm={k:check[k] for k in ['firmware_bytes','ram_static','foreground_bound','irq_reserve','remaining_margin']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');(a.out/'manifest.json').write_bytes(blobs['manifest.json']);(ROOT/'analysis/release220-verification.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(dict(passed=True,zip_sha256=r['zip_sha256'],decision=decision)))
if __name__=='__main__':main()
