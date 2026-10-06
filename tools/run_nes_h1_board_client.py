# SPDX-License-Identifier: MIT
# Reuse pinned033 actual-Mesen observer/auditor with explicit034 epoch-register adaptation.
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('build','out','mesen'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--epoch',type=int,required=True);a=p.parse_args();assert 1<=a.epoch<=65535
 r=Path(__file__).resolve().parents[1];out=a.out.resolve();assert not out.exists() and str(out).isascii();out.mkdir()
 manifest=json.loads((r/'analysis/h1-pattern-artifacts.json').read_text())
 known={e['path']:e['sha256'] for e in manifest['sources']}
 runner=r/'tools/run_nes_h1_client.py';observer=r/'snes/video_probe/capture_h1_pattern.lua'
 for f in (runner,observer):assert sha(f)==known[f.relative_to(r).as_posix()]
 lua=observer.read_text()
 lua=lua.replace("elseif n==6 then","elseif n==11 then result=BOARD_EPOCH&255\n elseif n==12 then result=BOARD_EPOCH>>8\n elseif n==6 then")
 lua=lua.replace('0x6000,0x600a','0x6000,0x600c').replace('cfg[2]+cfg[3]*256==1','cfg[2]+cfg[3]*256==BOARD_EPOCH')
 obs=out/'observer.lua';obs.write_text('local BOARD_EPOCH='+str(a.epoch)+'\n'+lua,encoding='utf-8',newline='\n')
 text=runner.read_text().replace('NES-H1-PATTERN-033','NES-H1-BOARD-034').replace('nes-h1-pattern-033.sfc','nes-h1-board-034.sfc')
 old="source=Path(__file__).resolve().parents[1]/'snes/video_probe/capture_h1_pattern.lua'"
 assert old in text;text=text.replace(old,'source=Path('+repr(str(obs))+')')
 py=out/'runner.py';py.write_text(text,encoding='utf-8',newline='\n')
 # Diagnostic pages already verified through034 RTL mux. Supply those exact captured bytes.
 # Repeat captured first three pages only; normal client consumes six pages.
 rtl=a.build.parent/'board-payload.bin';assert rtl.exists()
 data=rtl.read_bytes();assert len(data)==8192
 payload=out/'rtl-bytes.bin';payload.write_bytes(data[:6144]*2+data[:2048])
 cp=subprocess.run([sys.executable,'-B','-X','utf8',str(py),'--probe',str(a.build.resolve()),'--rtl-bytes',str(payload),'--out',str(out/'capture'),'--mesen',str(a.mesen.resolve())],capture_output=True)
 (out/'runner.log').write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,'runner.log'
 result=json.loads((out/'capture/result.json').read_text())
 meta={'candidate':'NES-H1-BOARD-034','epoch':a.epoch,'passed':result['passed'],'exact_pixels':result['exact_pixels'],'base_runner_sha256':sha(runner),'base_observer_sha256':sha(observer),'derived_runner_sha256':sha(py),'derived_observer_sha256':sha(obs),'driver_sha256':sha(__file__),'board_payload_sha256':sha(rtl),'scope':'Real CPU/PPU, explicit device model; repeated first3 actual034RTL pages for6page display test. Not cycle coupled.'}
 (out/'result.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta))
if __name__=='__main__':main()
