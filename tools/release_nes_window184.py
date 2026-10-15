# SPDX-License-Identifier: MIT
"""Release only the paired compact queue after functional/route/ARM/report gates."""
from pathlib import Path
import argparse,csv,hashlib,json,re,shutil,zipfile
from nes_game147 import ROOT,sha
from nes_cf68_pair_preflight import encode,decode
from nes_spi_boot import run
from nes_window184_compact import compact

def main():
 p=argparse.ArgumentParser()
 for n in ['prior','arm','check','report','fit','coupled','replay','unit','status','asm','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and not a.asm.exists();load=lambda p:json.loads(p.read_bytes());digest=lambda b:hashlib.sha256(b).hexdigest()
 gates={k:load(getattr(a,k)/'result.json') for k in ['check','report','coupled','replay','unit','status']}
 assert all(x['passed'] for x in gates.values())
 assert gates['check']['remaining_margin']>=1024
 assert gates['report']['source_sha256']==sha(a.arm/'src/nes_menu_diagnostic.c')
 for k in ['check','coupled','replay','status']:
  for n,h in gates[k]['public_sources'].items():assert sha(ROOT/n)==h,(k,n)
 for n,h in gates['coupled']['arm_sources'].items():assert sha(a.arm/'src'/n)==h,n
 for x,y in zip(gates['coupled']['cases'],gates['replay']['cases']):
  assert x['mode']==y['mode'] and x['events_sha256']==y['events_sha256']
 assert gates['coupled']['cases'][0]['commits']==7 and gates['coupled']['cases'][0]['acks']==219
 assert gates['unit']['compact_ack']
 q=compact((ROOT/'src/nes/diagnostic/nes_sink_queue184.sv').read_text())
 assert digest(q.encode())==gates['unit']['rtl_sha256']==gates['replay']['inputs']['nes_sink_queue184.sv']
 assert (a.fit/'nes_sink_spi165.sv').read_text()==q.replace('module nes_sink_queue184(','module nes_sink_spi165(')
 prep=load(a.arm/'preparation-window184-trial.json');pins=prep['copied']|prep['changed']|prep['added']
 for n,h in pins.items():assert sha(a.arm/n)==h,n
 fw=(a.arm/'src/obj-nes-100/firmware.stm').read_bytes();assert digest(fw)==gates['check']['firmware_sha256']
 for m in [b'NES GAME 184.nh1',b'game184.nes',b'fpga_n184.bi3',b'nes-progress-184.txt',b'nes-game-last-184.txt',b'sink_window_schema=184']:assert m in fw,m
 fprep=load(a.fit/'preparation.json')
 for n,h in fprep['sources'].items():assert sha(a.fit/n)==h,n
 assert (a.fit/'sink-program.hex').read_text()==(a.coupled/'client/sink-program.hex').read_text()
 for n in ['cdc-routed01.json','reply-routed01.json','conditional-io01.json']:assert (a.fit/n).exists()
 assert load(a.fit/'cdc-routed01.json')['routed_approval'] and load(a.fit/'reply-routed01.json')['physical_pass']
 io=load(a.fit/'conditional-io01.json');assert io['conditional_data_bounds_pass'] and io['native_payload_reset_pass']
 timing={}
 for view in ['nominal','implementation']:
  xs=list(csv.DictReader((a.fit/(view+'-clocks181.tsv')).open(),delimiter='\t'));assert len({x['corner'] for x in xs})==3
  timing[view]={k:min(float(x['slack']) for x in xs if x['kind']==k) for k in ['setup','hold']}
  assert min(timing[view].values())>=0
 ox=list(csv.DictReader((a.fit/'oamread181-paths.tsv').open(),delimiter='\t'));assert len(ox)==2220 and all(float(x['slack'])>=0 for x in ox)
 shutil.copytree(a.fit,a.asm)
 for label,args in [('asm184',['quartus_asm.exe','board']),('cpf184',['quartus_cpf.exe','-c','output_files/board.sof','output_files/board.rbf'])]:
  s=run([a.quartus_bin/args[0],*args[1:]],a.asm,label,300);assert 'successful' in s and '0 errors' in s,s[-2000:]
 for n,h in fprep['sources'].items():assert sha(a.asm/n)==h,n
 raw=(a.asm/'output_files/board.rbf').read_bytes();packed=encode(raw);assert decode(packed)==raw
 (a.asm/'fpga_n184.bi3').write_bytes(packed)
 assert sha(a.prior)=='a0d154f1b600c6ec9718a68b03f377212eb3bf8d3c1a1a2de75ab9e6f3cb5147'
 blobs={};preserved={}
 with zipfile.ZipFile(a.prior) as z:
  for n,item in json.loads(z.read('manifest.json'))['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256'],n
   if n.startswith(('01-GAME183-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('183','184') if n.startswith('01-') else n;blobs[dst]=b
    if dst not in ['01-GAME184-SD-ROOT/sd2snes/firmware.stm','01-GAME184-SD-ROOT/sd2snes/fpga_n184.bi3']:preserved[dst]=digest(b)
 blobs['01-GAME184-SD-ROOT/sd2snes/firmware.stm']=fw;blobs['01-GAME184-SD-ROOT/sd2snes/fpga_n184.bi3']=packed
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game184-ready.ko.md').read_bytes()
 decision=dict(trial_ready=True,physical=False,fps60_proven=False,window_packets=4,status_identity='F7',sink_version='1815',ingress_version='1813',
  run_ticks=6000,save_sram_used=False,remaining_margin=gates['check']['remaining_margin'],timing=timing,full_io_signoff=False,
  scope='Actual C/65816 via held queue, exact event replay in RTL; not simultaneous cycle-accurate CPU/MCU performance or hardware proof.')
 blobs['decision184.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES184-SMB3-WINDOW-VIDEO',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True);archive=a.out/'NES184-SMB3-WINDOW-VIDEO.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   i=zipfile.ZipInfo(n,(2026,10,15,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 result=dict(passed=True,zip_sha256=sha(archive),firmware_sha256=digest(fw),fpga_sha256=digest(packed),rbf_sha256=digest(raw),preserved=preserved,decision=decision,
  gates={k:sha(getattr(a,k)/'result.json') for k in gates},board_pins=len(fprep['sources']),arm_pins=len(pins),public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_window184.py','docs/nes-game184-ready.ko.md']})
 for n,b in [('result.json',(json.dumps(result,indent=2)+'\n').encode()),('manifest.json',blobs['manifest.json']),('START-HERE.ko.md',blobs['START-HERE.ko.md'])]:(a.out/n).write_bytes(b)
 print(json.dumps({k:v for k,v in result.items() if k!='preserved'}))
if __name__=='__main__':main()
