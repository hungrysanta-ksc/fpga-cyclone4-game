# SPDX-License-Identifier: MIT
"""Release wire2231 ARM223 + qualified counter224 board + exact SNES212 ROM."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from nes_counter224 import ROOT,BASE,sha

def read(p):return json.loads(p.read_bytes())
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
 d=BASE/'probes/nes-counter224';old223=BASE/'probes/nes-ingress223';arm=old223/'arm01'
 evidence=read(d/'analysis02.json');check=read(old223/'check01/result.json');asm=read(d/'asm01/result224.json');rom=read(d/'romcheck01/result.json')
 assert evidence['functional_pass'] and evidence['related_timing_pass'] and evidence['arm_pass']
 assert evidence['conditional_io']['conditional_data_bounds_pass'] and evidence['conditional_io']['native_payload_reset_pass']
 assert evidence['counter']['passed'] and evidence['counter']['sample_cases']==1024
 assert check['passed'] and check['remaining_margin']==1912 and asm['passed'] and not asm['new_fit'] and rom['passed']
 assert len(rom['checks'])==3 and all(x['matched_bytes']==4096 for x in rom['checks'])
 assert asm['client_sha256']==rom['expected_hex_sha256']==sha(BASE/'probes/nes-runtime213/asm01/sink-program.hex')
 for report in [evidence,evidence['counter'],check,asm,rom]:
  for n,h in report['public_sources'].items():assert sha(ROOT/n)==h,n
 prep=read(arm/'preparation-ingress223.json')
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(arm/n)==h,n
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 board=read(d/'source02/preparation224.json')
 assert set(n for n,h in board['sources'].items() if h!=board['baseline'][n])=={'nes_rom_spi.sv'}
 for place in ['source02','mapfit02']:
  for n,h in board['sources'].items():assert sha(d/place/n)==h,(place,n)
 for n,h in asm['baseline_pins'].items():assert sha(d/'mapfit02'/n)==h,n
 for n,h in asm['unchanged_routing_and_sources'].items():
  if n=='board.qsf' and sha(d/'asm01'/n)!=h:
   before=(d/'mapfit02'/n).read_text().replace('LAST_QUARTUS_VERSION "25.1std.0 Lite Edition"','LAST_QUARTUS_VERSION "25.1std.0 Standard Edition"').splitlines()
   eda=['','set_global_assignment -name EDA_SIMULATION_TOOL "QuestaSim (Verilog)"','set_global_assignment -name EDA_NETLIST_WRITER_OUTPUT_DIR simulation/modelsim -section_id eda_simulation','set_global_assignment -name EDA_OUTPUT_DATA_FORMAT "VERILOG HDL" -section_id eda_simulation']
   assert (d/'asm01'/n).read_text().splitlines()==before+eda,n
  else:assert sha(d/'asm01'/n)==h,n
 for x in rom['checks']:assert sha(d/'asm01/simulation/modelsim'/x['file'])==x['netlist_sha256']
 fw=(arm/'src/obj-nes-100/firmware.stm').read_bytes();fpga=(d/'asm01/fpga_n223.bi3').read_bytes()
 assert digest(fw)==check['firmware_sha256'] and sha(arm/'src/obj-nes-100/sd2snes.elf')==check['elf_sha256']
 assert digest(fpga)==asm['fpga_sha256']
 for marker in [b'NES GAME 223.nh1',b'game223.nes',b'fpga_n223.bi3',b'nes-progress-223.txt',b'nes-game-last-223.txt',b'nes-budget-223.txt',b'budget_schema=222',b'startup_schema=222']:assert marker in fw,marker
 old=BASE/'probes/nes-startup222/release01';oldr=read(old/'result.json');oldz=old/'NES222-SMB3-STARTUP.zip';assert sha(oldz)==oldr['zip_sha256']
 blobs={};preserved={};changed={'01-GAME223-SD-ROOT/sd2snes/firmware.stm','01-GAME223-SD-ROOT/sd2snes/fpga_n223.bi3'}
 with zipfile.ZipFile(oldz) as z:
  for n,item in read(old/'manifest.json')['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256']
   if n.startswith(('01-GAME222-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('222','223') if n.startswith('01-') else n;blobs[dst]=b
    if dst not in changed:preserved[dst]=digest(b)
 blobs['01-GAME223-SD-ROOT/sd2snes/firmware.stm']=fw;blobs['01-GAME223-SD-ROOT/sd2snes/fpga_n223.bi3']=fpga
 decision=dict(trial_ready=True,physical=False,fps60=False,new_fit=True,new_asm=True,current212_snes_rom=True,wire_version='2231',board_stage=224,arm_identity=223,remaining_margin=1912,run_ticks=6000,save_sram_unchanged=True,gbc164_unchanged=True)
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game223-ready.ko.md').read_bytes();blobs['decision223.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES223-SMB3-GEOMETRY',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()});blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 zout=a.out/'NES223-SMB3-GEOMETRY.zip'
 with zipfile.ZipFile(zout,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   i=zipfile.ZipInfo(n,(2026,10,17,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
 with zipfile.ZipFile(zout) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 result=dict(passed=True,decision=decision,zip_sha256=sha(zout),firmware_sha256=digest(fw),fpga_sha256=digest(fpga),preserved=preserved,prior222_zip_sha256=sha(oldz),
  gates={'board':sha(d/'analysis02.json'),'counter':sha(d/'test04/result.json'),'arm':sha(old223/'check01/result.json'),'ingress':sha(old223/'test01/result.json'),'asm':sha(d/'asm01/result224.json'),'rom':sha(d/'romcheck01/result.json')},
  public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_ingress223.py','docs/nes-game223-ready.ko.md']},
  arm={k:check[k] for k in ['firmware_bytes','ram_static','foreground_bound','irq_reserve','remaining_margin']})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');(a.out/'manifest.json').write_bytes(blobs['manifest.json'])
 (ROOT/'analysis/release223-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(passed=True,zip_sha256=result['zip_sha256'],decision=decision)))
if __name__=='__main__':main()
