# SPDX-License-Identifier: MIT
"""Gate the vblank-client164 trial, preserving163 sound and restoration files."""
from pathlib import Path
import argparse,json,zipfile,hashlib
from nes_game147 import ROOT,ROM_SHA,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','asm','arm','arm-check','client','reuse','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 e=a.baseline/'nes-game163/evidence';m=json.loads((ROOT/'analysis/game163-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 old=e/'release/NES163-SMB3-SPC-AUDIO.zip';assert sha(old)==m['package']['zip_sha256']
 client=json.loads((a.client/'result.json').read_bytes());reuse=json.loads((a.reuse/'result.json').read_bytes());arm=json.loads((a.arm_check/'result.json').read_bytes());fpga=json.loads((a.asm/'result164.json').read_bytes())
 assert all(x['passed'] for x in [client,reuse,fpga]) and arm['strong_nmi']
 assert len(client['cases'])==3 and client['cases'][-1]['rejected']
 for c in client['cases'][:2]:assert c['exact_rgb_frames']==2 and c['max_visible_dma_end_line']<262 and c['every_visible_frame_pad_polled']
 assert client['program_sha256']==fpga['program_sha256']==sha(a.asm/'game-program.hex')
 for n,h in client['sources'].items():assert sha(ROOT/n)==h,n
 for n,h in fpga['unchanged_routing_and_sources'].items():assert sha(a.asm/n)==h==sha(e/'asm'/n),n
 for n,h in reuse['source_sha256'].items():assert sha(a.arm/n)==h,n
 fw=a.arm/'src/obj-nes-100/firmware.stm';bi=a.asm/'fpga_n164.bi3'
 assert sha(fw)==arm['firmware_sha256'] and sha(bi)==fpga['packed_sha256']
 digest=lambda b:hashlib.sha256(b).hexdigest();blobs={};preserved={}
 with zipfile.ZipFile(old) as z:
  for n,v in json.loads(z.read('manifest.json'))['files'].items():
   b=z.read(n);assert len(b)==v['bytes'] and digest(b)==v['sha256']
   if n.startswith(('01-GAME163-SD-ROOT/','02-RESTORE044-SD-ROOT/')):
    dst=n.replace('163','164');blobs[dst]=b
    if n.startswith('02-') or not n.endswith(('firmware.stm','fpga_n163.bi3')):preserved[dst]=digest(b)
 assert digest(blobs['01-GAME164-SD-ROOT/sd2snes/nes/game164.nes'])==ROM_SHA
 assert blobs['01-GAME164-SD-ROOT/NES GAME 164.nh1']==b''
 blobs['01-GAME164-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes();blobs['01-GAME164-SD-ROOT/sd2snes/fpga_n164.bi3']=bi.read_bytes()
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game164-instructions.ko.md').read_bytes()
 decision=dict(candidate='NES-GAME-164',rtl_reused='162',ids=['6B','E5'],normal_trial_ready=True,visible_upload_chunks=[5632]*10+[1024],initial_full_blank_dma=True,post_reveal_forced_blank=False,atomic_frame_flip=False,smooth_60fps=False,physical_video_pending=True,physical_audio_baseline='163 user confirmed',held_input_fixed=False,run_budget_seconds=60,reset_logging=False,new_map_fit=False,preserved=preserved,limits=['Progressive partial updates and snapshot age remain; no faster full-frame rate claim','Synthetic SNES test is not physical video timing/pad proof','Same162 RTL/placement/timing conditional limits and163 SPC boot','Install firmware and FPGA together;6B/E5/A9 do not uniquely identify164 client'])
 blobs['decision164.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES164-SMB3-VBLANK-VIDEO',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()});blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
 a.out.mkdir(parents=True);archive=a.out/'NES164-SMB3-VBLANK-VIDEO.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 for n in ['START-HERE.ko.md','decision164.json','manifest.json']:(a.out/n).write_bytes(blobs[n])
 result=dict(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,members=len(blobs),firmware_sha256=sha(fw),fpga_sha256=sha(bi),normal_trial_ready=True,physical_video_pending=True,preserved=preserved)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
