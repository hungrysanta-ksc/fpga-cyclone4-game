# SPDX-License-Identifier: MIT
"""Replay original event spacing through the online RTL and check reconstruction."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from collections import defaultdict
from nes_native_commands165 import Fetch,Consumer,Unsupported,reference_rgb
from nes_native_rows165 import RowConsumer
from nes_native_compact165 import decode,equivalent
from test_nes_native_commands165 import fixture
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['stream','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 files=['src/nes/diagnostic/nes_native_compact165.sv','tests/nes-functional/native_compact165_tb.sv']
 for n in files:shutil.copy2(ROOT/n,a.out/Path(n).name)
 def run(exe,args,name):
  with (a.out/(name+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  text=(a.out/(name+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-3000:]
 run('vlib',['work'],'vlib');run('vlog',['-sv','nes_native_compact165.sv','native_compact165_tb.sv'],'vlog')
 results=[]
 def case(name,events,expected=True,mode=0):
  events=sorted(events);previous=events[0][0]-1 if events else 0;lines=[]
  for tick,word in events:
   assert tick>previous;lines.append(f'{tick-previous} {word:016x}\n');previous=tick
  (a.out/(name+'.tsv')).write_text(''.join(lines))
  run('vsim',['-c','work.native_compact165_tb','+INPUT='+name+'.tsv','+OUTPUT='+name+'.dump',f'+MODE={mode}',
   '-do','onerror {quit -code 1}; run -all; quit -f'],name)
  info,words=decode(a.out/(name+'.dump'))
  if expected is not None:assert info['valid']==expected,(name,info)
  if info['valid']:assert equivalent(words,[w for t,w in events]),name
  info['name']=name;info['events']=len(events);results.append(info);return words
 def schedule(words):
  events=[]
  for word in words:
   f=Fetch.unpack(word);tick=f.row*1364+(f.rank*32 if f.obj else 280+f.x*32)
   events.append((tick+1,word))
  return sorted(events)
 words,rows,tiles=fixture(0);synthetic=schedule(words)
 case('synthetic',synthetic)
 # Input cannot stall the core. A late row-copy collision is an invalid scene.
 collision=list(synthetic);index=next(i for i,(t,w) in enumerate(collision) if not Fetch.unpack(w).obj and Fetch.unpack(w).row==1)
 collision[index]=(collision[index-1][0]+1,collision[index][1])
 # Explicitly place BG row1 column0 one clock after row0's final BG cell.
 row0last=next(t for t,w in synthetic if not Fetch.unpack(w).obj and Fetch.unpack(w).row==0 and Fetch.unpack(w).x==32)
 collision[index]=(row0last+1,collision[index][1]);case('copy-overrun',collision,False)
 case('source-fault-at-start',[],False,1)
 case('empty-scene',[],False)
 first_bg=next(i for i,(t,w) in enumerate(synthetic) if not Fetch.unpack(w).obj)
 case('missing-cell',synthetic[:first_bg]+synthetic[first_bg+1:],False)
 overflow=[]
 for t,w in synthetic:
  f=Fetch.unpack(w)
  if not f.obj:f=Fetch(f.tile,0,f.slot,f.row,f.x,f.attr,False,0)
  overflow.append((t,f.pack()))
 case('BG-capacity',overflow,False)
 plain=[(t,w) for t,w in synthetic if not Fetch.unpack(w).obj]
 for y in range(129):plain.append((y*1364+1,Fetch(20,0,0,y,10,0,True,0).pack()))
 case('OBJ-capacity',plain,False)
 exceptional=[]
 for t,w in synthetic:
  f=Fetch.unpack(w)
  if not f.obj and f.x==1:f=Fetch(f.tile,(f.fine+1)%8,f.slot,f.row,f.x,f.attr,False,0)
  exceptional.append((t,f.pack()))
 case('exception-capacity',exceptional,False)
 events=defaultdict(list);states={};rowsets=defaultdict(dict)
 for line in (a.stream/'events.tsv').read_text().splitlines():
  g,t,w=line.split();events[int(g)].append((int(t),int(w,16)))
 for line in (a.stream/'states.tsv').read_text().splitlines():
  g,f,v,e,rv,re_=line.split();states[int(g)]=dict(frame=int(f),fetch_valid=int(v),fetch_errors=int(e,16),raster_valid=int(rv),raster_errors=int(re_,16))
 for line in (a.stream/'rows.tsv').read_text().splitlines():
  g,y,x,mask,palette=line.split();v=int(palette,16)
  rowsets[int(g)][int(y)]=(int(x),int(mask,16),tuple((v>>(i*6))&63 for i in range(32)))
 chrdata=bytes(int(v,16) for v in (a.stream/'chr.hex').read_text().split());physical={t:chrdata[t*16:t*16+16] for t in range(8192)}
 game=[];accepted=[]
 for g,state in sorted(states.items()):
  ev=events[g];n_bg=sum(not Fetch.unpack(w).obj for t,w in ev)
  item=dict(generation=g,**state,events=len(ev),background_events=n_bg,masks=sorted(set(m for x,m,p in rowsets[g].values())))
  if n_bg!=7392:item['deferred']='incomplete BG (rendering disabled or changed)';game.append(item);continue
  output=case(f'game-{g}',ev,None)
  item['compact']=results[-1]
  if not results[-1]['valid']:item['deferred']='compact capacity or protocol rejection';game.append(item);continue
  rows=[rowsets[g][y] for y in range(224)]
  # Actual per-cell addresses represent coarse/fine VRAM changes. The old
  # raw-v/t snapshot's blanket scroll-access bit remains recorded, not erased.
  # Other raster failures and fetch pairing errors still reject this reference.
  if not state['fetch_valid'] or state['raster_errors']&~16:item['deferred']='source rejected';game.append(item);continue
  try:packet=RowConsumer().prepare(output,rows,physical)
  except Unsupported as e:item['deferred']=str(e);game.append(item);continue
  rgb=reference_rgb(output,rows,physical)
  original=[int(v,16) for v in (a.stream/f'game-{state["frame"]}.hex').read_text().split()][8*256:232*256]
  from build_nes_game164 import palette as colors
  import struct
  lut=[bytes((((v>>s)&31)<<3)|(((v>>s)&31)>>2) for s in [0,5,10]) for v in struct.unpack('<64H',colors())]
  expected=b''.join(lut[v&63] for v in original)
  assert rgb==expected,(g,'NES raster versus actual pixels',sum(x!=y for x,y in zip(rgb,expected)))
  item.update(pixels_equal=True,initial_payload=packet['payload'],map_groups=packet['groups'],objects=packet['fragments'],derived_patterns=packet['derived_patterns'])
  accepted.append(g);game.append(item)
 result=dict(passed=True,rtl_cases=results,game=game,accepted_game_generations=accepted,
  public_sources={n:sha(ROOT/n) for n in files+['tools/nes_native_compact165.py','tools/test_nes_native_compact165.py']},
  scope='Online RTL replay at original actual-game event spacing; reconstruction equals source descriptors. CHR supplied by private ROM on PC. No live host/CHR fill/fit/hardware proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
