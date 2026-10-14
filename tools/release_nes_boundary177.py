# SPDX-License-Identifier: MIT
"""Pair output-only177 observation with exact174 runtime and preserved rollback."""
from pathlib import Path
import argparse,json,zipfile,hashlib,re
from nes_game147 import ROOT,sha
from nes_cf68_pair_preflight import encode,decode
from nes_spi_boot import run

def main():
 p=argparse.ArgumentParser()
 for n in ['prior','prior-arm','arm','arm-check','fit','fit-check','report','quartus-bin','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();load=lambda p:json.loads(p.read_bytes());assert not a.out.exists()
 ar=load(a.arm_check/'result.json');f=load(a.fit_check);rp=load(a.report/'result.json')
 assert ar['passed'] and ar['remaining_margin']>=1024 and rp['passed']
 assert f['passed'] and f['nominal']['passed'] and f['io']['conditional_data_bounds_pass'] and f['io']['native_payload_reset_pass']
 for result in [ar,f]:
  for n,h in result['public_sources'].items():assert sha(ROOT/n)==h,n
 assert rp['source_sha256']==sha(a.arm/'src/nes_menu_diagnostic.c') and 'bytes=3925 capacity=4096' in rp['output']
 # Runtime reuse must be byte-exact; three permitted source changes are labels only.
 permitted={'src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION'}
 preserved_sources={}
 for old in (a.prior_arm/'src').rglob('*'):
  if not old.is_file() or old.suffix not in ['.c','.h','.inc','.s','.S'] and old.name not in ['VERSION','Makefile']:continue
  if any(part.startswith('obj') for part in old.relative_to(a.prior_arm).parts):continue
  n=old.relative_to(a.prior_arm).as_posix();new=a.arm/n
  if n in permitted:
   expected=old.read_text().replace('174','177').replace('LAST16_NES_CLOCKS_INCLUDING_FAULT','LAST16_BOUNDARY177_LOW22')
   assert new.read_text()==expected,n
  else:assert sha(old)==sha(new),n;preserved_sources[n]=sha(new)
 pins=load(a.fit/'preparation.json')['sources'];assert pins==f['sources']
 for n,h in pins.items():assert sha(a.fit/n)==h,n
 mif,=a.fit.glob('db/board.ram*_nes_sink_bus165_*.hdl.mif')
 rows=re.findall(r'^\s*(\d+)\s*:\s*([01]{8});',mif.read_text(),re.M);assert len(rows)==4096
 image={int(i):int(v,2) for i,v in rows}
 assert bytes(image[i] for i in range(4096))==bytes.fromhex((a.fit/'sink-program.hex').read_text())
 assert sha(a.fit/'sink-program.hex')=='e1c350b76fea340a1ed9fa643929ce80bd0371b748b374d57ce8d90d85188fc5'
 for label,args in [('asm177',['quartus_asm.exe','board']),('cpf177',['quartus_cpf.exe','-c','output_files/board.sof','output_files/board.rbf'])]:
  log=run([a.quartus_bin/args[0],*args[1:]],a.fit,label,300);assert 'successful' in log and '0 errors' in log,log[-2000:]
 for n,h in pins.items():assert sha(a.fit/n)==h,n
 raw=(a.fit/'output_files/board.rbf').read_bytes();packed=encode(raw);assert decode(packed)==raw
 (a.fit/'fpga_n177.bi3').write_bytes(packed)
 assert sha(a.prior)=='6624455010e05fe425ec1b81fd105e2eaddf21ef795470aa047da03c77940468'
 digest=lambda b:hashlib.sha256(b).hexdigest();blobs={};preserved={}
 with zipfile.ZipFile(a.prior) as z:
  for n,item in json.loads(z.read('manifest.json'))['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256']
   if n.startswith(('01-GAME174-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('174','177') if n.startswith('01-') else n;blobs[dst]=b
    if dst not in ['01-GAME177-SD-ROOT/sd2snes/firmware.stm','01-GAME177-SD-ROOT/sd2snes/fpga_n177.bi3']:preserved[dst]=digest(b)
 fw=a.arm/'src/obj-nes-100/firmware.stm';assert sha(fw)==ar['firmware_sha256']
 assert b'NES GAME 177.nh1' in fw.read_bytes() and b'/sd2snes/fpga_n177.bi3' in fw.read_bytes()
 blobs['01-GAME177-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes();blobs['01-GAME177-SD-ROOT/sd2snes/fpga_n177.bi3']=packed
 assert '01-GAME177-SD-ROOT/NES GAME 177.nh1' in blobs and '01-GAME177-SD-ROOT/sd2snes/nes/game177.nes' in blobs
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game177-ready.ko.md').read_bytes()
 decision=dict(trial_ready=True,physical=False,video_fix_proven=False,fps60_proven=False,run_ticks_after_ready=6000,
  run_sd_writes=False,save_sram_used=False,remaining_margin=ar['remaining_margin'],nominal_setup_ns=float(f['nominal']['worst_setup']['slack']),
  full_io_signoff=False,history_wire_version=1,history_low22_tag=6,history_kind='LAST16_BOUNDARY177_LOW22',runtime_same174=True)
 blobs['decision177.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest={'package':'NES177-SMB3-BOUNDARY','files':{n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()}}
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 archive=a.out/'NES177-SMB3-BOUNDARY.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,14,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 for n in ['START-HERE.ko.md','manifest.json','decision177.json']:(a.out/n).write_bytes(blobs[n])
 r=dict(passed=True,zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,firmware_sha256=sha(fw),fpga_sha256=digest(packed),rbf_sha256=digest(raw),
  snes_mif_matches_4096_bytes=True,snes_program_sha256=sha(a.fit/'sink-program.hex'),preserved=preserved,preserved_mcu_sources=preserved_sources,decision=decision,
  gates=dict(fit_check_sha256=sha(a.fit_check),arm_check_sha256=sha(a.arm_check/'result.json'),report_sha256=sha(a.report/'result.json')),
  public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_boundary177.py','docs/nes-game177-ready.ko.md','tools/nes_cf68_pair_preflight.py','tools/test_nes_startup170_report.py','tools/test_nes_sink168_report.py']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print('PASS177 PACKAGE',r['zip_sha256'])
if __name__=='__main__':main()
