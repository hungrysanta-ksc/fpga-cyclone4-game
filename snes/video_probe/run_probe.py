"""Run isolated Mesen and compare actual PPU RGB. SPDX-License-Identifier: MIT."""
import argparse,subprocess,json,hashlib,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--mesen',type=Path,required=True);p.add_argument('--probe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
if not str(a.out.resolve()).isascii():raise SystemExit('Use a fresh ASCII --out: Windows Lua io cannot open Unicode paths')
a.out.mkdir(parents=True,exist_ok=False);out=a.out.resolve();probe=a.probe.resolve();exe=a.mesen.resolve()
lua=Path(__file__).with_name('capture.lua').read_text(encoding='utf-8-sig')
(out/'capture.lua').write_text('local OUT_DIR='+json.dumps(out.as_posix(),ensure_ascii=False)+'\n'+lua,encoding='utf-8')
with (out/'mesen.log').open('wb') as f:
 r=subprocess.run([str(exe),'--testRunner',str(out/'capture.lua'),str(probe/'probe.sfc'),'--timeout=20','--doNotSaveSettings','--enableStdout'],stdout=f,stderr=subprocess.STDOUT,timeout=30)
result=dict(returncode=r.returncode,exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),core_sha256=hashlib.sha256(exe.with_name('MesenCore.dll').read_bytes()).hexdigest(),rom_sha256=hashlib.sha256((probe/'probe.sfc').read_bytes()).hexdigest(),frames=[])
expected=json.loads((probe/'expected.json').read_text())
for frame in (10,11):
 f=out/f'frame-{frame}.txt'
 if not f.exists():result['frames'].append(dict(frame=frame,error='capture missing'));continue
 lines=f.read_text().splitlines();w,h=map(int,lines[0].split());marker=int(lines[1].split()[1])
 pixels=[int(row[i:i+6],16) for row in lines[2:] for i in range(0,len(row),6)]
 assert len(pixels)==w*h
 # Mesen SNES raw output has 239 rows and may double horizontal/vertical output.
 # No search for a favorable alignment: source y=0 is screen y=0, full visible area.
 sx=w//256;sy=h//239
 if w not in (256,512) or h not in (239,478):
  result['frames'].append(dict(frame=frame,width=w,height=h,error='unexpected output geometry'));continue
 bad=[]
 for y in range(239):
  for x in range(256):
   want=expected['lut'][expected['pixels'][y*256+x]]
   for yy in range(sy):
    for xx in range(sx):
     got=pixels[(y*sy+yy)*w+x*sx+xx]
     if want!=got:bad.append((x,y,want,got))
 result['frames'].append(dict(frame=frame,width=w,height=h,marker=marker,different_output_pixels=len(bad),first_difference=bad[0] if bad else None,capture_sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
result['pass']=r.returncode==0 and all(f.get('different_output_pixels')==0 and f.get('marker')==165 for f in result['frames'])
result['source_hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),Path(__file__).with_name('capture.lua'))}
result['mesen_settings_sha256']=hashlib.sha256(exe.with_name('settings.json').read_bytes()).hexdigest()
result['ui_sha256']=hashlib.sha256(exe.with_name('Mesen.dll').read_bytes()).hexdigest()
result['scope']='actual SNES PPU: '+json.loads((probe/'manifest.json').read_text())['scope']+'; source row 239 remains unrepresented'
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
raise SystemExit(0 if result['pass'] else 1)
