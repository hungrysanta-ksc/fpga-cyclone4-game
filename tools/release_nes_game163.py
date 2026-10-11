# SPDX-License-Identifier: MIT
"""Gate and package MCU163 plus ROM-content-only update of162 FPGA."""
from pathlib import Path
import argparse,json,zipfile,hashlib
from nes_game147 import ROOT,ROM_SHA,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','asm','arm','arm-check','client','status','host','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 e=a.baseline/'nes-game162/evidence';m=json.loads((ROOT/'analysis/game162-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 old=e/'release/NES162-SMB3-AUDIO.zip';assert sha(old)==m['package']['zip_sha256']
 client=json.loads((a.client/'result.json').read_bytes());status=json.loads((a.status/'result.json').read_bytes());host=json.loads((a.host/'result.json').read_bytes());arm=json.loads((a.arm_check/'result.json').read_bytes());fpga=json.loads((a.asm/'result163.json').read_bytes())
 assert all(x['passed'] for x in [client,status,host,fpga]) and arm['strong_nmi']
 assert [x['status_hex'] for x in client['cases']]==['A9','E1','E2','E3','E4','E5']
 assert client['program_sha256']==fpga['program_sha256']==sha(a.asm/'game-program.hex')
 assert status['rtl_sha256']==sha(a.asm/'nes_screen_status151.sv') and status['cases']==54
 for n,h in client['sources'].items():assert sha(ROOT/n)==h,n
 for n,h in fpga['unchanged_routing_and_sources'].items():assert sha(a.asm/n)==h==sha(e/'asm'/n),n
 ap=json.loads((a.arm/'preparation163.json').read_bytes());assert set(ap['changed'])=={'src/VERSION','src/nes_menu_diagnostic.c','src/nes_checkpoint112.c'}
 for n,h in ap['copied'].items():assert sha(a.arm/n)==ap['changed'].get(n,h),n
 assert host['source_sha256']==sha(a.arm/'src/nes_run136.inc') and host['format_source_sha256']==sha(a.arm/'src/nes_menu_diagnostic.c')
 fw=a.arm/'src/obj-nes-100/firmware.stm';bi=a.asm/'fpga_n163.bi3';assert sha(fw)==arm['firmware_sha256'] and sha(bi)==fpga['packed_sha256']
 digest=lambda b:hashlib.sha256(b).hexdigest();blobs={};preserved={}
 with zipfile.ZipFile(old) as z:
  for n,v in json.loads(z.read('manifest.json'))['files'].items():
   b=z.read(n);assert len(b)==v['bytes'] and digest(b)==v['sha256']
   if n.startswith(('01-GAME162-SD-ROOT/','02-RESTORE044-SD-ROOT/')):
    dst=n.replace('162','163');blobs[dst]=b
    if n.startswith('02-') or not n.endswith(('firmware.stm','fpga_n162.bi3')):preserved[dst]=digest(b)
 assert digest(blobs['01-GAME163-SD-ROOT/sd2snes/nes/game163.nes'])==ROM_SHA
 assert blobs['01-GAME163-SD-ROOT/NES GAME 163.nh1']==b''
 blobs['01-GAME163-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes();blobs['01-GAME163-SD-ROOT/sd2snes/fpga_n163.bi3']=bi.read_bytes()
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game163-instructions.ko.md').read_bytes()
 decision=dict(candidate='NES-GAME-163',rtl_reused='162',ids=['6B','E5'],client_status=['A9','E1','E2','E3','E4','E5'],physical_audio=False,normal_trial_ready=True,continuous_video=False,held_input_fixed=False,run_budget_seconds=60,reset_logging=False,new_map_fit=False,preserved=preserved,limits=['SPC FLG readback does not prove audible cartridge audio','Same162 RTL/placement/timing conditional limits, same161 video/pad/60s','Warm reset and analog path still need physical game test'])
 blobs['decision163.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES163-SMB3-SPC-AUDIO',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()});blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
 a.out.mkdir(parents=True);archive=a.out/'NES163-SMB3-SPC-AUDIO.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 for n in ['START-HERE.ko.md','decision163.json','manifest.json']:(a.out/n).write_bytes(blobs[n])
 result=dict(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,members=len(blobs),firmware_sha256=sha(fw),fpga_sha256=sha(bi),normal_trial_ready=True,physical_audio=False,preserved=preserved)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
