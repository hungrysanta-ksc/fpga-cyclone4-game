# SPDX-License-Identifier: MIT
"""MCU-only170 pair; retain169 FPGA and164 restore exactly, verify prerequisites."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['prior','arm','arm-check','test','report','rom-check','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 assert sha(a.prior)=='fc2c3ca8c3b9e629bf7ed152fafcd6c2dfe987f9ea7e9d1240b073f6a98ee15d'
 ar=json.loads((a.arm_check/'result.json').read_bytes());test=json.loads((a.test/'result.json').read_bytes());rp=json.loads((a.report/'result.json').read_bytes());rom=json.loads((a.rom_check/'result.json').read_bytes())
 assert all(q['passed'] for q in [ar,test,rp,rom])
 assert ar['remaining_margin']>=1024 and ar['io_trace_bytes']==20
 for q in [ar,test,rom]:
  for n,h in q['public_sources'].items():assert sha(ROOT/n)==h,n
 prep=json.loads((a.arm/'preparation-startup170.json').read_bytes())
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(a.arm/n)==h,n
 assert sha(a.arm/'src/nes_menu_diagnostic.c')==rp['source_sha256']
 for public,dest in [('nes_sink_spi170.c','nes_sink_spi165.c'),('nes_sink_io170.c','nes_sink_io170.c'),('nes_sink_io170.h','nes_sink_io170.h')]:
  assert (ROOT/'src/nes/firmware'/public).read_text()==(a.arm/'src'/dest).read_text()
 fw=a.arm/'src/obj-nes-100/firmware.stm';assert sha(fw)==ar['firmware_sha256']
 digest=lambda b:hashlib.sha256(b).hexdigest();blobs={};preserved={}
 with zipfile.ZipFile(a.prior) as z:
  manifest=json.loads(z.read('manifest.json'))
  for n,v in manifest['files'].items():
   b=z.read(n);assert len(b)==v['bytes'] and digest(b)==v['sha256']
   if n.startswith(('01-GAME169-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('169','170') if n.startswith('01-') else n;blobs[dst]=b
    if not dst.endswith('01-GAME170-SD-ROOT/sd2snes/firmware.stm'):preserved[dst]=digest(b)
 blobs['01-GAME170-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes()
 assert digest(blobs['01-GAME170-SD-ROOT/sd2snes/fpga_n170.bi3'])=='6ba983350c27e2e78111cf0a7ed6ec18ff56676f248148aa42ddf313de90329d'
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game170-ready.ko.md').read_bytes()
 decision={'trial_ready':True,'physical':False,'video_fix_claimed':False,'same_FPGA_SNES_as169':True,'new_FPGA_build':False,'run_ticks':6000,'sink_poll_limit':65536,'run_sd_writes':False,'save_sram_used':False,'remaining_margin':ar['remaining_margin']}
 blobs['decision170.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest={'package':'NES170-SMB3-FIRST-EXCHANGE','files':{n:{'bytes':len(b),'sha256':digest(b)} for n,b in blobs.items()}}
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 archive=a.out/'NES170-SMB3-FIRST-EXCHANGE.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,13,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 for n in ['START-HERE.ko.md','manifest.json','decision170.json']:(a.out/n).write_bytes(blobs[n])
 r={'passed':True,'zip_sha256':sha(archive),'zip_bytes':archive.stat().st_size,'firmware_sha256':sha(fw),'fpga_sha256':digest(blobs['01-GAME170-SD-ROOT/sd2snes/fpga_n170.bi3']),'preserved':preserved,'physical':False,'public_sources':{n:sha(ROOT/n) for n in ['tools/release_nes_startup170.py','docs/nes-game170-ready.ko.md']}}
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS170 PACKAGE',r['zip_sha256'])
if __name__=='__main__':main()
