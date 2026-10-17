# SPDX-License-Identifier: MIT
"""Package only a matching checked213 ARM + ROM-updated207 FPGA pair."""
from pathlib import Path
import argparse,difflib,hashlib,json,zipfile
from nes_runtime213 import ROOT,BASE,sha
PUBLIC=['tools/nes_runtime213.py','tools/test_nes_runtime213.py','tools/check_nes_runtime213_arm.py',
 'tools/test_nes_join213.py','tools/test_nes_binding213.py','tools/assemble_nes_paired213.py',
 'tools/test_nes_runtime213_budget.py','tools/release_nes_runtime213.py',
 'docs/nes-runtime213-contract.ko.md','docs/nes-game213-ready.ko.md']
def read(p):return json.loads(p.read_bytes())
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
 d=BASE/'probes/nes-runtime213';arm=d/'arm01';prep=read(arm/'preparation-runtime213.json')
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(arm/n)==h,n
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 selected=['test05','check01','report01','budget01','join02','binding02','romcheck01']
 results={n:read(d/n/'result.json') for n in selected};assert all(r['passed'] for r in results.values())
 check=results['check01'];assert check['remaining_margin']>=1024
 assert check['remaining_margin']==5016 and check['foreground_bound']==32088 and check['irq_reserve']==508
 for n,h in check['public_sources'].items():assert sha(ROOT/n)==h,n
 for n,h in results['test05']['source_hashes'].items():
  if n.startswith('nes_'):assert sha(arm/'src'/n)==h,n
 assert results['report01']['source_sha256']==results['budget01']['menu_sha256']==sha(arm/'src/nes_menu_diagnostic.c')
 assert 'bytes=4047 capacity=4096' in results['report01']['output'] and 'format_max=2415' in results['budget01']['output']
 assert results['budget01']['budget_sha256']==sha(arm/'src/nes_budget210.c')
 join=results['join02'];assert join['actual_c_rtl_snes_transaction_join']
 for n,h in join['source_pins'].items():assert sha(BASE/n)==h,n
 assert sha(d/'join02/runner-source.py')==sha(ROOT/'tools/test_nes_join213.py')
 for c in join['cases']:
  assert c['passed'] and c['commits']==(3 if c['mode']=='normal' else 1)
  if c['mode']=='normal':assert c['reference208_pixels']==183552 and c['single_vblank_commits']==1
 # Queue proof used identical join01 messages; simulation status timing differs.
 for c in results['binding02']['cases']:
  folder=d/'join02'/c['mode']
  for n,h in c['input_pins'].items():assert sha(folder/n)==h,n
  assert c['packets']==(80 if c['mode']=='normal' else 35)
 for n,h in results['binding02']['public_sources'].items():assert sha(ROOT/n)==h,n
 baseline=BASE/'probes/nes-board207/mapfit02';assembly=read(d/'asm01/result213.json');assert assembly['passed']
 for n,h in assembly['baseline_pins'].items():assert sha(baseline/n)==h,n
 for n,h in assembly['unchanged_routing_and_sources'].items():
  if n!='board.qsf' and not n.startswith('simulation/'):assert sha(d/'asm01'/n)==h,n
 for n,h in assembly['public_sources'].items():assert sha(ROOT/n)==h,n
 q0=(baseline/'board.qsf').read_text().splitlines();q1=(d/'asm01/board.qsf').read_text().splitlines()
 # EDA edits output metadata after ASM, never placement/clock/IO settings.
 allowed=('set_global_assignment -name LAST_QUARTUS_VERSION ',
 'set_global_assignment -name EDA_SIMULATION_TOOL ',
 'set_global_assignment -name EDA_NETLIST_WRITER_OUTPUT_DIR ',
 'set_global_assignment -name EDA_OUTPUT_DATA_FORMAT ')
 def substantive(lines):return [s for s in lines if s and not s.startswith(allowed)]
 assert substantive(q0)==substantive(q1)
 client=BASE/'probes/nes-dirty212/test09/client'
 assert assembly['client_sha256']==sha(client/'sink-program.hex')==sha(d/'asm01/sink-program.hex')
 for c in results['romcheck01']['checks']:
  assert c['matched_bytes']==4096 and sha(d/'asm01/simulation/modelsim'/c['file'])==c['netlist_sha256']
  assert c['rom_sha256']==digest(bytes.fromhex((client/'sink-program.hex').read_text()))
 frozen=BASE/'probes/nes-dirty212';manifest=read(frozen/'evidence01/manifest.json')
 for n,h in manifest.items():assert sha(frozen/n)==h,n
 fw=(arm/'src/obj-nes-100/firmware.stm').read_bytes();fpga=(d/'asm01/fpga_n213.bi3').read_bytes()
 assert digest(fw)==check['firmware_sha256'] and sha(arm/'src/obj-nes-100/sd2snes.elf')==check['elf_sha256']
 assert digest(fpga)==assembly['fpga_sha256']
 for marker in [b'NES GAME 213.nh1',b'game213.nes',b'fpga_n213.bi3',b'nes-progress-213.txt',b'nes-game-last-213.txt',b'nes-budget-213.txt']:assert marker in fw,marker
 old=BASE/'probes/nes-budget210/release01';oldresult=read(old/'result.json');oldzip=old/'NES210-SMB3-SCROLL-BUDGET.zip'
 assert sha(oldzip)==oldresult['zip_sha256']
 blobs={};preserved={}
 with zipfile.ZipFile(oldzip) as z:
  for n,item in read(old/'manifest.json')['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256'],n
   if n.startswith(('01-GAME210-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('210','213') if n.startswith('01-') else n;blobs[dst]=b
    if dst not in ['01-GAME213-SD-ROOT/sd2snes/firmware.stm','01-GAME213-SD-ROOT/sd2snes/fpga_n213.bi3']:preserved[dst]=digest(b)
 blobs['01-GAME213-SD-ROOT/sd2snes/firmware.stm']=fw;blobs['01-GAME213-SD-ROOT/sd2snes/fpga_n213.bi3']=fpga
 assert digest(blobs['01-GAME213-SD-ROOT/sd2snes/nes/game213.nes'])=='dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'
 assert blobs['01-GAME213-SD-ROOT/NES GAME 213.nh1']==b''
 decision=dict(trial_ready=True,physical=False,fps60_proven=False,actual_scroll_measured=False,
  new_fit=False,new_asm=True,rom_only_update=True,run_ticks=6000,remaining_margin=5016,
  resident_bytes=3200,save_sram_used=False,report_max=4047,budget_max=2415,
  scope='Production resident213 RUN + sparse212 consumer. Local joins/pixels/abort/ARM/ROM verified; physical scrolling remains required.')
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game213-ready.ko.md').read_bytes()
 blobs['decision213.json']=(json.dumps(decision,indent=2)+'\n').encode()
 package=dict(package='NES213-SMB3-RESIDENT-DIRTY',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(package,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 zout=a.out/'NES213-SMB3-RESIDENT-DIRTY.zip'
 with zipfile.ZipFile(zout,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   i=zipfile.ZipInfo(n,(2026,10,17,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
 with zipfile.ZipFile(zout) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 r=dict(passed=True,selected=['arm01',*selected,'asm01','release01'],decision=decision,
  firmware_sha256=digest(fw),fpga_sha256=digest(fpga),zip_sha256=sha(zout),preserved=preserved,
  prior212_manifest_sha256=sha(frozen/'evidence01/manifest.json'),prior212_files=len(manifest),
  gates={n:sha(d/n/'result.json') for n in selected},assembly_gate=sha(d/'asm01/result213.json'),
  public_sources={n:sha(ROOT/n) for n in PUBLIC},joined=join['cases'],arm={k:check[k] for k in ['firmware_bytes','ram_static','foreground_bound','irq_reserve','remaining_margin']},
  next='User213 first-level scroll video + progress/game/budget TXT. Do not infer60fps from synthetic warm frame; remaining ingress/scrollmap/overlap16.67ms budget.')
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
 (a.out/'manifest.json').write_bytes(blobs['manifest.json']);(a.out/'START-HERE.ko.md').write_bytes(blobs['START-HERE.ko.md'])
 (a.out/'qsf-normalized.diff').write_text('\n'.join(difflib.unified_diff(q0,q1,fromfile='207',tofile='213'))+'\n',encoding='utf8')
 (ROOT/'analysis/runtime213-verification.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(passed=True,zip_sha256=r['zip_sha256'],decision=decision)))
if __name__=='__main__':main()
