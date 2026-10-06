"""Compare dynamic actual SNES PPU frames and DMA transaction traces. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,json,hashlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--mesen',type=Path,required=True);p.add_argument('--probe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--frames',type=int,default=64);a=p.parse_args()
assert 16<=a.frames<=192
out=a.out.resolve();assert str(out).isascii();out.mkdir(parents=True,exist_ok=False)
probe=a.probe.resolve();exe=a.mesen.resolve();manifest=json.loads((probe/'manifest.json').read_text())
script=Path(__file__).with_name('capture_stream.lua')
(out/'capture.lua').write_text('local OUT_DIR='+json.dumps(out.as_posix())+'\nlocal CAPTURE_FRAMES='+str(a.frames)+'\n'+script.read_text(encoding='utf-8-sig'),encoding='utf-8',newline='\n')
with (out/'mesen.log').open('wb') as log:
 r=subprocess.run([str(exe),'--testRunner',str(out/'capture.lua'),str(probe/'stream.sfc'),'--timeout=50','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true'],stdout=log,stderr=subprocess.STDOUT,timeout=60)
frames=[];errors=[]
meta=out/'frames.tsv'
if meta.exists():
 for row in meta.read_text().splitlines():
  index,emu_frame,clock,frame,epoch,slot,error,w,h=map(int,row.split('\t'))
  actual=(out/f'frame-{index:03}.rgb').read_bytes();expected=(probe/f'expected-{frame%16:02}.rgb').read_bytes()
  if (w,h)!=(256,239) or len(actual)!=len(expected):errors.append('geometry');continue
  bad=[n//3 for n in range(0,len(actual),3) if actual[n:n+3]!=expected[n:n+3]]
  want=index if manifest['fault']!='reset' or index!=7 else 6
  want_epoch=1 if manifest['fault']=='reset' and index>=7 else 0
  if frame!=want:errors.append(f'frame_sequence:{index}:{frame}!={want}')
  if epoch!=want_epoch:errors.append(f'epoch:{index}:{epoch}!={want_epoch}')
  if error:errors.append(f'host_error:{index}:{error}')
  if bad:errors.append(f'pixels:{index}:{len(bad)}')
  frames.append(dict(index=index,emulator_frame=emu_frame,frame_id=frame,epoch=epoch,slot=slot,different_pixels=len(bad),first_xy=[bad[0]%256,bad[0]//256] if bad else None,sha256=hashlib.sha256(actual).hexdigest()))
trace=[]
if (out/'trace.tsv').exists():
 for row in (out/'trace.tsv').read_text().splitlines():
  v=row.split('\t');trace.append(dict(zip(['kind','value','clock','emulator_frame','line','hclock','display','attempt','epoch','active_slot','pending_slot','vram_lo','vram_hi','target','size_lo','size_hi'],[v[0]]+list(map(int,v[1:])))))
transactions=[];current=None
for t in trace:
 if t['kind']=='phase' and t['value']==1:current=dict(startup=t['display']==255,attempt=t['attempt'],start_clock=t['clock'],start_line=t['line'],start_hclock=t['hclock'],dma_bytes=0,staging_safe=True,dmas=[])
 elif current and t['kind']=='dma':
  length=t['size_lo']+256*t['size_hi'];current['dma_bytes']+=length;current['dmas'].append(t)
  if t['target']==0x18:
   addr=t['vram_lo']+256*t['vram_hi'];lo,hi=(0x3000,0x3400) if t['active_slot']==0 else (0x3400,0x3800)
   maplo,maphi=(0x0800,0x0c00) if t['active_slot']==0 else (0x0c00,0x1000)
   pending=t['pending_slot'];plo,phi=(0x3000+pending*0x400,0x3400+pending*0x400);mlo,mhi=(0x0800+pending*0x400,0x0c00+pending*0x400)
   end=addr+(length+1)//2
   if not (plo<=addr<end<=phi or mlo<=addr<end<=mhi) or pending==t['active_slot']:current['staging_safe']=False
 elif current and t['kind']=='phase' and t['value'] in (3,4,238):
  duration=t['clock']-current['start_clock'];deadline=(262-240)*1364-4
  # Full master-clock interval includes refresh; reserve next line 0 completely.
  margin=deadline-(current['start_line']-240)*1364-current['start_hclock']-duration
  current.update(end_clock=t['clock'],end_line=t['line'],duration_master_clocks=duration,deadline_margin_master_clocks=margin,outcome={3:'commit',4:'reset_abort',238:'halt'}[t['value']])
  if not (225 if current['startup'] else 240)<=current['start_line']<=261 or margin<0 or not (225 if current['startup'] else 240)<=t['line']<=261:errors.append('deadline:'+str(t['attempt']))
  if not current['staging_safe']:errors.append('visible_slot_overwrite:'+str(t['attempt']))
  transactions.append(current);current=None
if len(frames)!=a.frames:errors.append('capture_count')
if not transactions:errors.append('no_transactions')
if any(t['kind']=='brightness' and t['value']&128 for t in trace):errors.append('steady_forced_blank')
result=dict(candidate=manifest['candidate'],fault=manifest['fault'],diagnostic=manifest['diagnostic'],sprites=manifest['sprites'],returncode=r.returncode,
 passed=r.returncode==0 and not errors,errors=errors,frames=frames,transactions=transactions,
 max_payload_bytes=max((t['dma_bytes'] for t in transactions),default=0),max_duration_master_clocks=max((t['duration_master_clocks'] for t in transactions),default=0),
 min_deadline_margin_master_clocks=min((t['deadline_margin_master_clocks'] for t in transactions),default=None),
 source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),script]},
 tool_hashes={n:hashlib.sha256((exe.parent/n).read_bytes()).hexdigest() for n in ['Mesen.exe','Mesen.dll','MesenCore.dll','settings.json']},
 manifest_sha256=hashlib.sha256((probe/'manifest.json').read_bytes()).hexdigest(),emulator_overrides=['--snes.disableFrameSkipping=true'],scope=manifest['scope'],source_height=240,displayed_height=239)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('frames','transactions','source_hashes','tool_hashes')},indent=2))
raise SystemExit(0 if result['passed'] else 1)
