# SPDX-License-Identifier: MIT
"""Fail-closed209 package from frozen207 routing,203 RUN and208/209 joins."""
from pathlib import Path
import argparse,json,hashlib,zipfile
from nes_board204 import ROOT,BASE,sha
from nes_bulk194_evidence import verify_archive
from nes_cf68_pair_preflight import decode

PUBLIC=['tools/test_nes_binding209.py','tools/nes_paired209.py','tools/check_nes_paired209_arm.py',
 'tools/test_nes_paired209_report.py','tools/assemble_nes_paired209.py','tools/inspect_nes_paired209_rom.py',
 'tools/release_nes_paired209.py','docs/nes-binding209-contract.ko.md','docs/nes-game209-ready.ko.md']
def read(p):return json.loads(p.read_bytes())
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
 d=BASE/'probes/nes-binding209';old=read(ROOT/'analysis/join208-verification.json');assert old['passed']
 archives=[]
 for x in old['prior_archives']:
  y=verify_archive(x['name']);assert y==x;archives.append(y)
 assert sha(BASE/'probes/nes-join208/manifest01.json')=='9d4a88fd90282bafef7c0c6c50d9b8c186baa365791d73e5c0c12f5145954d7d'
 archives.append(verify_archive('nes-join208'));assert len(archives)==24
 for n,h in old['source_pins'].items():assert sha(ROOT/n)==h,n
 board=read(ROOT/'analysis/board207-verification.json')
 assert board['related_timing_passed'] and board['epoch_reset_passed'] and board['conditional_io_passed']
 test=read(d/'test02/result.json');check=read(d/'check02/result.json');report=read(d/'report02/result.json');rom=read(d/'romcheck02/result.json');assembly=read(d/'asm01/result209.json')
 assert all(x['passed'] for x in [test,check,report,rom,assembly]) and check['remaining_margin']>=1024
 for x in [test,check,rom,assembly]:
  for n,h in x['public_sources'].items():assert sha(ROOT/n)==h,n
 for n,h in test['board_pins'].items():assert sha(BASE/'probes/nes-board207/source02'/n)==h,n
 for c in test['cases']:
  for n,h in c['input_pins'].items():assert sha(BASE/'probes/nes-join208/test08'/c['mode']/n)==h,n
  assert sha(d/'test02'/(c['mode']+'-events.txt'))==c['events_sha256']
 arm=d/'arm01';prep=read(arm/'preparation-paired209.json');pins=prep['copied']|prep['changed']|prep['added']
 assert set(prep['changed'])=={'src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION'}
 for n,h in pins.items():assert sha(arm/n)==h,n
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 assert report['source_sha256']==sha(arm/'src/nes_menu_diagnostic.c') and 'bytes=4047 capacity=4096' in report['output']
 for n in ['nes_native_runtime165.c','nes_native165.c','nes_plan191.c','nes_plan_service200.c','nes_native_sink165.c','nes_sink_window184.c']:
  assert sha(arm/'src'/n)==sha(BASE/'probes/nes-join208/test08'/n),n
 fw=(arm/'src/obj-nes-100/firmware.stm').read_bytes();assert digest(fw)==check['firmware_sha256']
 assert sha(arm/'src/obj-nes-100/sd2snes.elf')==check['elf_sha256']
 for m in [b'NES GAME 209.nh1',b'game209.nes',b'fpga_n209.bi3',b'nes-progress-209.txt',b'nes-game-last-209.txt',b'NES-GAME209-DEV',b'plan_error=%u']:assert m in fw,m
 for m in [b'NES GAME 186.nh1',b'game186.nes',b'fpga_n186.bi3',b'NES-META203-DEV']:assert m not in fw,m
 fit=BASE/'probes/nes-board207/mapfit02'
 for n,h in assembly['baseline_pins'].items():assert sha(fit/n)==h,n
 for n,h in assembly['unchanged_assembly_sources_and_routing'].items():
  if n!='board.qsf':assert sha(d/'asm01'/n)==h,n
 # EDA rewrites line endings/version metadata after ASM. Permit exactly this
 # known output-only suffix and edition label; compare every other setting.
 q=(fit/'board.qsf').read_text().replace('LAST_QUARTUS_VERSION "25.1std.0 Lite Edition"','LAST_QUARTUS_VERSION "25.1std.0 Standard Edition"')
 q+='\nset_global_assignment -name EDA_SIMULATION_TOOL "QuestaSim (Verilog)"\nset_global_assignment -name EDA_NETLIST_WRITER_OUTPUT_DIR simulation/modelsim -section_id eda_simulation\nset_global_assignment -name EDA_OUTPUT_DATA_FORMAT "VERILOG HDL" -section_id eda_simulation'
 assert (d/'asm01/board.qsf').read_text()==q
 packed=(d/'asm01/fpga_n209.bi3').read_bytes();raw=(d/'asm01/output_files/board.rbf').read_bytes()
 assert decode(packed)==raw and digest(packed)==assembly['fpga_sha256'] and digest(raw)==assembly['rbf_sha256']
 compact=bytes.fromhex((fit/'sink-program.hex').read_text());sfc=(BASE/'probes/nes-join208/test08/sink165.sfc').read_bytes()
 assert len(compact)==4096 and compact==sfc[:0xfc0]+sfc[0x7fc0:] and assembly['client_sha256']==sha(fit/'sink-program.hex')==rom['expected_hex_sha256']
 assert len(rom['checks'])==3
 for c in rom['checks']:
  assert c['matched_bytes']==4096 and c['rom_sha256']==digest(compact)
  assert sha(d/'asm01/simulation/modelsim'/c['file'])==c['netlist_sha256']
 assert read(ROOT/'analysis/scroll193-measurement-plan.json')['collected_runs']==[]
 prior=BASE/'probes/nes-paired186/release01';prev=read(prior/'result.json');zpath=prior/'NES186-SMB3-COPY-GROUP.zip';assert sha(zpath)==prev['zip_sha256'] and prev['decision']['trial_ready']
 blobs={};preserved={}
 with zipfile.ZipFile(zpath) as z:
  for n,item in read(prior/'manifest.json')['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256'],n
   if n.startswith(('01-GAME186-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('186','209') if n.startswith('01-') else n;blobs[dst]=b
    if dst not in ['01-GAME209-SD-ROOT/sd2snes/firmware.stm','01-GAME209-SD-ROOT/sd2snes/fpga_n209.bi3']:preserved[dst]=digest(b)
 blobs['01-GAME209-SD-ROOT/sd2snes/firmware.stm']=fw;blobs['01-GAME209-SD-ROOT/sd2snes/fpga_n209.bi3']=packed
 assert digest(blobs['01-GAME209-SD-ROOT/sd2snes/nes/game209.nes'])=='dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'
 decision=dict(trial_ready=True,physical=False,fps60_proven=False,ingress_version='2031',sink_version='1941',plan_status_version=4,window_schema=184,
  remaining_margin=check['remaining_margin'],run_ticks=6000,save_sram_used=False,new_fit=False,full_io_signoff=False,
  scope='First direct-tile hardware trial; selected207 routing, actual208 transaction join,209 queue replay and ARM identity. Scene-specific cadence and physical contention unmeasured.')
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game209-ready.ko.md').read_bytes()
 blobs['decision209.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES209-SMB3-DIRECT-TILES',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True);archive=a.out/'NES209-SMB3-DIRECT-TILES.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   i=zipfile.ZipInfo(n,(2026,10,16,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 r=dict(passed=True,selected=['test02','arm01','check02','report02','asm01','romcheck02','release01'],decision=decision,
  zip_sha256=sha(archive),firmware_sha256=digest(fw),fpga_sha256=digest(packed),rbf_sha256=digest(raw),preserved=preserved,prior_archives=archives,
  queue_packets=sum(c['packets'] for c in test['cases']),queue_checks=sum(c['checks'] for c in test['cases']),mux_checks=test['mux_truth_table_checks'],
  arm_bytes=len(fw),remaining_margin=check['remaining_margin'],report_max_bytes=4047,postfit_rom_outputs=3,
  gates={n:sha(d/n/'result.json') for n in ['test02','check02','report02','romcheck02']},assembly_sha256=sha(d/'asm01/result209.json'),
  public_sources={n:sha(ROOT/n) for n in PUBLIC},actual_scroll_measured=False,new_fit=False,new_arm=True,new_asm=True,new_package=True,physical=False,
  next='User209 FIRSTLEVELSCROLL: tile1+A then RIGHT+B held with repeated A press/release; two TXT and20-30s scrolling video. No repeated044 restore or unchanged FIT/codec loops; do not infer60fps from aggregate ACKs.')
 for n,b in [('result.json',(json.dumps(r,indent=2)+'\n').encode()),('manifest.json',blobs['manifest.json']),('START-HERE.ko.md',blobs['START-HERE.ko.md'])]:(a.out/n).write_bytes(b)
 (ROOT/'analysis/binding209-verification.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps({k:r[k] for k in ['passed','zip_sha256','firmware_sha256','fpga_sha256','queue_packets','queue_checks','remaining_margin','report_max_bytes']}))
if __name__=='__main__':main()
