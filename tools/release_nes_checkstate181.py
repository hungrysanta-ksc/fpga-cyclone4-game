# SPDX-License-Identifier: MIT
"""Package the routed181 board with the exact approved1813/1815 ARM pair."""
from pathlib import Path
import argparse,json,zipfile,hashlib,shutil
from nes_game147 import ROOT,sha
from nes_cf68_pair_preflight import encode,decode
from nes_spi_boot import run
from nes_stream181 import build

def main():
 p=argparse.ArgumentParser()
 for n in ['prior','arm','arm-check','fit','fit-check','report','asm','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and not a.asm.exists()
 load=lambda p:json.loads(p.read_bytes());digest=lambda b:hashlib.sha256(b).hexdigest()
 f=load(a.fit_check);ar=load(a.arm_check/'result.json');rp=load(a.report/'result.json')
 assert f['evidence_verified'] and f['nominal_candidate_eligible'] and f['functional']['passed']
 assert float(f['timing']['implementation']['worst_setup']['slack'])>=0
 assert ar['passed'] and ar['remaining_margin']>=1024
 assert rp['passed'] and rp['source_sha256']==sha(a.arm/'src/nes_menu_diagnostic.c')
 for n,h in ar['public_sources'].items():assert sha(ROOT/n)==h,n
 prep=load(a.arm/'preparation-paired181.json');pins=prep['copied']|prep['changed']|prep['added']
 assert prep['ingress_version']=='1813' and prep['sink_version']=='1815' and prep['expired_bg_workspace_reuse']
 for n,h in pins.items():assert sha(a.arm/n)==h,n
 fw=a.arm/'src/obj-nes-100/firmware.stm';assert sha(fw)==ar['firmware_sha256']
 for marker in [b'NES GAME 181.nh1',b'/sd2snes/fpga_n181.bi3',b'/sd2snes/nes/game181.nes',b'nes-progress-181.txt',b'nes-game-last-181.txt']:
  assert marker in fw.read_bytes(),marker
 fpins=load(a.fit/'preparation.json')['sources'];assert fpins==f['sources']
 for n,h in fpins.items():assert sha(a.fit/n)==h,n
 # Assembler works on a new DB copy. Preserve the original FIT and STA evidence.
 shutil.copytree(a.fit,a.asm)
 client=build(a.asm/'client-reproduced1815')
 assert (a.asm/'sink-program.hex').read_bytes()==(a.asm/'client-reproduced1815/sink-program.hex').read_bytes()
 assert (a.asm/'client-reproduced1815/body.bin').stat().st_size==3643
 for label,args in [('asm181',['quartus_asm.exe','board']),('cpf181',['quartus_cpf.exe','-c','output_files/board.sof','output_files/board.rbf'])]:
  log=run([a.quartus_bin/args[0],*args[1:]],a.asm,label,300);assert 'successful' in log and '0 errors' in log,log[-2000:]
 for n,h in fpins.items():assert sha(a.asm/n)==sha(a.fit/n)==h,n
 raw=(a.asm/'output_files/board.rbf').read_bytes();packed=encode(raw);assert decode(packed)==raw
 (a.asm/'fpga_n181.bi3').write_bytes(packed)
 assert sha(a.prior)=='8eede14b49701530529d737815685f4f92f3d41f784c93a7abdfa03dd279cb3a'
 blobs={};preserved={}
 with zipfile.ZipFile(a.prior) as z:
  for n,item in json.loads(z.read('manifest.json'))['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256']
   if n.startswith(('01-GAME180-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('180','181') if n.startswith('01-') else n;blobs[dst]=b
    if dst not in ['01-GAME181-SD-ROOT/sd2snes/firmware.stm','01-GAME181-SD-ROOT/sd2snes/fpga_n181.bi3']:preserved[dst]=digest(b)
 assert '01-GAME181-SD-ROOT/NES GAME 181.nh1' in blobs
 rom=blobs['01-GAME181-SD-ROOT/sd2snes/nes/game181.nes']
 assert digest(rom)=='dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'
 blobs['01-GAME181-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes()
 blobs['01-GAME181-SD-ROOT/sd2snes/fpga_n181.bi3']=packed
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game181-ready.ko.md').read_bytes()
 decision=dict(trial_ready=True,physical=False,video_fix_proven=False,fps60_proven=False,
  ingress_version='1813',sink_version='1815',run_ticks_after_ready=6000,run_sd_writes=False,save_sram_used=False,
  remaining_margin=ar['remaining_margin'],nominal_setup_ns=float(f['timing']['nominal']['worst_setup']['slack']),
  implementation_setup_ns=float(f['timing']['implementation']['worst_setup']['slack']),full_io_signoff=False,
  spi_min_ss_high_ns=2000,command_latency_changed=False,history_kind='LAST16_EPISODE180_V3',raw7_minimum_egress_model_ms=22.154)
 blobs['decision181.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES181-SMB3-ROW-VIDEO',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 archive=a.out/'NES181-SMB3-ROW-VIDEO.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,15,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 for n in ['START-HERE.ko.md','manifest.json','decision181.json']:(a.out/n).write_bytes(blobs[n])
 result=dict(passed=True,zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,firmware_sha256=sha(fw),fpga_sha256=digest(packed),rbf_sha256=digest(raw),
  preserved=preserved,decision=decision,client=client,arm_source_count=len(pins),board_source_count=len(fpins),
  gates=dict(fit_check_sha256=sha(a.fit_check),arm_check_sha256=sha(a.arm_check/'result.json'),report_sha256=sha(a.report/'result.json')),
  public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_checkstate181.py','docs/nes-game181-ready.ko.md','tools/nes_cf68_pair_preflight.py','tools/nes_stream181.py','tools/test_nes_startup170_report.py','tools/test_nes_sink168_report.py']})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['preserved','client','public_sources']}))
if __name__=='__main__':main()
