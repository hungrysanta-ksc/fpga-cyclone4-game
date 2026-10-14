# SPDX-License-Identifier: MIT
"""Package only the gated171 FIFO candidate; preserve ROM and164 restore."""
from pathlib import Path
import argparse,json,zipfile,hashlib,re
from nes_game147 import ROOT,sha
from nes_cf68_pair_preflight import encode,decode
from nes_spi_boot import run
def main():
 p=argparse.ArgumentParser()
 for n in ['prior','arm','arm-check','fit','report','quartus-bin','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 ar=json.loads((a.arm_check/'result.json').read_bytes());fit=json.loads((a.fit/'result171.json').read_bytes());rp=json.loads((a.report/'result.json').read_bytes())
 assert ar['passed'] and ar['remaining_margin']>=1024 and fit['passed'] and rp['passed']
 assert fit['same_limits'] and fit['io']['native_payload_reset_pass']
 for q in [ar,fit]:
  for n,h in q['public_sources'].items():assert sha(ROOT/n)==h,n
 prep=json.loads((a.arm/'preparation-prefetch171.json').read_bytes())
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(a.arm/n)==h,n
 assert rp['source_sha256']==sha(a.arm/'src/nes_menu_diagnostic.c')
 pins=json.loads((a.fit/'preparation.json').read_bytes())['sources']
 for n,h in pins.items():assert sha(a.fit/n)==h,n
 mif,=a.fit.glob('db/board.ram*_nes_sink_bus165_*.hdl.mif')
 rows=re.findall(r'^\s*(\d+)\s*:\s*([01]{8});',mif.read_text(),re.M)
 assert len(rows)==4096
 image={int(i):int(v,2) for i,v in rows}
 assert bytes(image[i] for i in range(4096))==bytes.fromhex((a.fit/'sink-program.hex').read_text())
 for label,args in [('asm171',['quartus_asm.exe','board']),('cpf171',['quartus_cpf.exe','-c','output_files/board.sof','output_files/board.rbf'])]:
  log=run([a.quartus_bin/args[0],*args[1:]],a.fit,label,300);assert 'successful' in log and '0 errors' in log,log[-2000:]
 for n,h in pins.items():assert sha(a.fit/n)==h,n
 raw=(a.fit/'output_files/board.rbf').read_bytes();packed=encode(raw);assert decode(packed)==raw
 (a.fit/'fpga_n171.bi3').write_bytes(packed)
 assert sha(a.prior)=='4da282813234ac6d5502f0c256657b398ff91c6d52a090cda0f7bc5c65a2d12c'
 digest=lambda b:hashlib.sha256(b).hexdigest();blobs={};preserved={}
 with zipfile.ZipFile(a.prior) as z:
  m=json.loads(z.read('manifest.json'))
  for n,item in m['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256']
   if n.startswith(('01-GAME170-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('170','171') if n.startswith('01-') else n;blobs[dst]=b
    if dst not in ['01-GAME171-SD-ROOT/sd2snes/firmware.stm','01-GAME171-SD-ROOT/sd2snes/fpga_n171.bi3']:preserved[dst]=digest(b)
 fw=a.arm/'src/obj-nes-100/firmware.stm';assert sha(fw)==ar['firmware_sha256']
 blobs['01-GAME171-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes();blobs['01-GAME171-SD-ROOT/sd2snes/fpga_n171.bi3']=packed
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game171-ready.ko.md').read_bytes()
 decision=dict(trial_ready=True,physical=False,continuous_video_proven=False,frame_rate_approved=False,run_ticks=6000,run_sd_writes=False,save_sram_used=False,fifo_entries=256,fifo_entry_bits=27,same_psram_arbiter=True,fill_total_cycles=16777216,export_total_cycles=33554432,remaining_margin=ar['remaining_margin'],full_external_io_approved=False)
 blobs['decision171.json']=(json.dumps(decision,indent=2)+'\n').encode()
 m={'package':'NES171-SMB3-CHR-FIFO','files':{n:{'bytes':len(b),'sha256':digest(b)} for n,b in blobs.items()}}
 blobs['manifest.json']=(json.dumps(m,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 archive=a.out/'NES171-SMB3-CHR-FIFO.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,13,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 for n in ['START-HERE.ko.md','manifest.json','decision171.json']:(a.out/n).write_bytes(blobs[n])
 r=dict(passed=True,zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,firmware_sha256=sha(fw),fpga_sha256=digest(packed),rbf_sha256=digest(raw),snes_mif_matches_4096_bytes=True,snes_program_sha256=sha(a.fit/'sink-program.hex'),preserved=preserved,physical=False,public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_prefetch171.py','docs/nes-game171-ready.ko.md']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS171 PACKAGE',r['zip_sha256'])
if __name__=='__main__':main()
