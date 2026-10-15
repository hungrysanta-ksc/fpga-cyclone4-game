# SPDX-License-Identifier: MIT
"""Package186 only after linking candidate evidence to actual ARM and ROM bytes."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from nes_game147 import ROOT,sha
from nes_cf68_pair_preflight import decode

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prior185','candidate','arm','check','report','assembly','romcheck','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 read=lambda p:json.loads(p.read_bytes());digest=lambda b:hashlib.sha256(b).hexdigest()
 # These frozen archives bind functional, routing and candidate evidence.
 archives=[(a.prior185,'manifest01.json','92e0180212f22fb7e851067cf3aafe12efb7797c60493042712257a2e529ec62'),(a.baseline,'manifest02.json','dc63e102b959f408a7dcd653cd722c08808111873a16dffb3cc2453b10e9939a'),
           (a.candidate,'manifest01.json','81746540486ecf9391bdf06395b3614aaf8130aa73c36f7807834bac9a3eb8df')]
 for root,name,h in archives:
  assert sha(root/name)==h
  for n,v in read(root/name).items():assert sha(root/n)==v,(root,n)
 analysis=read(a.candidate/'analysis.json');assert analysis['passed']
 for n,h in analysis['public_sources'].items():assert sha(ROOT/n)==h,n
 check=read(a.check/'result.json');report=read(a.report/'result.json');rom=read(a.romcheck/'result.json');assembly=read(a.assembly/'result186.json')
 assert check['passed'] and check['remaining_margin']>=1024 and report['passed'] and rom['passed'] and assembly['passed']
 for gate in [check,rom,assembly]:
  for n,h in gate['public_sources'].items():assert sha(ROOT/n)==h,n
 prep=read(a.arm/'preparation-paired186.json');pins=prep['copied']|prep['changed']|prep['added']
 for n,h in pins.items():assert sha(a.arm/n)==h,n
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 for n,h in prep['candidate_pins'].items():assert sha(a.candidate/'build01'/n)==h==sha(a.arm/'src'/n),n
 native=read(a.candidate/'test01/result.json');assert native['passed']
 for n,h in prep['candidate_pins'].items():assert native['pins'][n]==h,n
 assert report['source_sha256']==sha(a.arm/'src/nes_menu_diagnostic.c')
 fw=(a.arm/'src/obj-nes-100/firmware.stm').read_bytes();assert digest(fw)==check['firmware_sha256']
 for m in [b'NES GAME 186.nh1',b'game186.nes',b'fpga_n186.bi3',b'nes-progress-186.txt',b'nes-game-last-186.txt',b'sink_window_schema=184']:assert m in fw,m
 client=a.candidate/'build01/client';assert assembly['client_sha256']==sha(client/'sink-program.hex')==sha(a.assembly/'sink-program.hex')==rom['expected_hex_sha256']
 rawrom=bytes.fromhex((client/'sink-program.hex').read_text());sfc=(client/'sink165.sfc').read_bytes()
 assert len(rawrom)==4096 and len(sfc)==32768 and rawrom==sfc[:0xfc0]+sfc[0x7fc0:]
 assert all(c['rom_sha256']==digest(rawrom) and c['matched_bytes']==4096 for c in rom['checks']) and len(rom['checks'])==4
 assert analysis['pad']['passed'] and analysis['pad']['service_bytes_unchanged']
 pad=analysis['pad'];body=(client/'body.bin').read_bytes()
 assert digest(body[pad['start']:pad['end']])==pad['service_sha256']
 assert pad['prior_verified_sfc']=='5625332d228b6658a7bf07caaaade7030002a03be9324d0e760c06076a6a55e1'
 assert analysis['coupled']['snes_rom']==digest(sfc) and analysis['coupled']['passed'] and analysis['extra_boundaries']['passed']
 fit=a.baseline/'evidence/route02'
 for n,h in assembly['baseline_pins'].items():assert sha(fit/n)==h,n
 for n,h in assembly['unchanged_routing_and_sources'].items():assert sha(a.assembly/n)==h,n
 old=read(a.baseline/'release01/result.json');assert old['passed'] and old['decision']['trial_ready']
 for v in old['decision']['timing'].values():assert min(v.values())>=0
 rbf=(a.assembly/'output_files/board.rbf').read_bytes();packed=(a.assembly/'fpga_n186.bi3').read_bytes()
 assert decode(packed)==rbf and digest(packed)==assembly['fpga_sha256'] and digest(rbf)==assembly['rbf_sha256']
 previous=read(a.prior185/'release02/result.json');assert previous['passed']
 prior=a.prior185/'release02/NES185-SMB3-MAP-INHERIT.zip';assert sha(prior)==previous['zip_sha256']
 blobs={};preserved={}
 with zipfile.ZipFile(prior) as z:
  for n,item in read_zip_manifest(z).items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256'],n
   if n.startswith(('01-GAME185-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('185','186') if n.startswith('01-') else n;blobs[dst]=b
    if dst not in ['01-GAME186-SD-ROOT/sd2snes/firmware.stm','01-GAME186-SD-ROOT/sd2snes/fpga_n186.bi3']:preserved[dst]=digest(b)
 blobs['01-GAME186-SD-ROOT/sd2snes/firmware.stm']=fw;blobs['01-GAME186-SD-ROOT/sd2snes/fpga_n186.bi3']=packed
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game186-ready.ko.md').read_bytes()
 decision=dict(trial_ready=True,physical=False,fps60_proven=False,sink_version='1861',ingress_version='1813',window_schema=184,window_packets=4,run_ticks=6000,save_sram_used=False,new_fit=False,held_input_fix=True,remaining_margin=check['remaining_margin'],timing=old['decision']['timing'],full_io_signoff=False,scope='Verified candidate and full ARM link; ROM-only CDB/ASM with post-fit4096-byte atom check. No new physical performance result.')
 blobs['decision186.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES186-SMB3-COPY-GROUP',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True);archive=a.out/'NES186-SMB3-COPY-GROUP.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   i=zipfile.ZipInfo(n,(2026,10,15,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 result=dict(passed=True,zip_sha256=sha(archive),firmware_sha256=digest(fw),fpga_sha256=digest(packed),rbf_sha256=digest(rbf),preserved=preserved,decision=decision,arm_pins=len(pins),routing_pins=len(assembly['unchanged_routing_and_sources']),archive_pins={root.name+'/'+name:h for root,name,h in archives},gates={k:sha(v/'result.json') for k,v in [('check',a.check),('report',a.report),('romcheck',a.romcheck)]},assembly_sha256=sha(a.assembly/'result186.json'),public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_paired186.py','docs/nes-game186-ready.ko.md']})
 for n,b in [('result.json',(json.dumps(result,indent=2)+'\n').encode()),('manifest.json',blobs['manifest.json']),('START-HERE.ko.md',blobs['START-HERE.ko.md'])]:(a.out/n).write_bytes(b)
 print(json.dumps({k:v for k,v in result.items() if k!='preserved'}))

def read_zip_manifest(z):return json.loads(z.read('manifest.json'))['files']
if __name__=='__main__':main()
