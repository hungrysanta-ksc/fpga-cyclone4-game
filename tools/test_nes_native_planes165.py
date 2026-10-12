# SPDX-License-Identifier: MIT
"""Actual pair replay -> directly connected bounded producer -> exact NES pixels."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,struct
from collections import defaultdict
from nes_game147 import ROOT,sha
from nes_native_planes165 import decode,unpack,pack,PlaneConsumer,reference_planes_rgb
from nes_native_compact165 import equivalent
from nes_native_commands165 import Fetch,Unsupported
from build_nes_game164 import palette as colors

def main():
 p=argparse.ArgumentParser()
 for n in ['stream','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 trace=defaultdict(list);old=defaultdict(list);pairs={};rowsets=defaultdict(dict)
 for line in (a.stream/'replay.tsv').read_text().splitlines():trace[int(line.split()[0])].append(line)
 for line in (a.stream/'events.tsv').read_text().splitlines():
  g,t,w=line.split();old[int(g)].append(int(w,16))
 for line in (a.stream/'pairs.tsv').read_text().splitlines():
  v=line.split();g=int(v[0]);assert g not in pairs
  low,high,logical_low,logical_high,desc_low,desc_high=map(lambda s:int(s,16),v[4:10])
  assert low>>3==((high^8)>>3) and logical_low>>3==((logical_high^8)>>3)
  assert (desc_low^desc_high)&~(7<<13)==0 and (low&7)!=(high&7) and v[12:15]==['1','1','1']
  pairs[g]=dict(frame=g,line=int(v[2]),dot=int(v[3]),low_address=f'{low:06x}',high_address=f'{high:06x}',
   low_fine=low&7,high_fine=high&7,low_byte=v[10],high_byte=v[11],descriptor=pack(Fetch.unpack(desc_high),low&7))
 for line in (a.stream/'rows.tsv').read_text().splitlines():
  g,y,x,m,v=line.split();v=int(v,16);rowsets[int(g)][int(y)]=(int(x),int(m,16),tuple((v>>(i*6))&63 for i in range(32)))
 assert set(pairs)=={12,14,15,16,18,19,20},set(pairs)
 raw=bytes(int(v,16) for v in (a.stream/'chr.hex').read_text().split());tiles={t:raw[t*16:t*16+16] for t in range(8192)}
 for item in pairs.values():
  assert raw[int(item['low_address'],16)-0x200000]==int(item['low_byte'],16)
  assert raw[int(item['high_address'],16)-0x200000]==int(item['high_byte'],16)
 files=['src/nes/diagnostic/nes_native_fetch165.sv','src/nes/diagnostic/nes_native_planes165.sv',
  'src/nes/diagnostic/nes_native_compact_planes165.sv','tests/nes-functional/native_planes165_tb.sv']
 for n in files:shutil.copy2(ROOT/n,a.out/Path(n).name)
 def run(exe,args,name):
  with (a.out/(name+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  s=(a.out/(name+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4000:]
  return s
 run('vlib',['work'],'vlib');run('vlog',['-sv',*[Path(n).name for n in files]],'vlog')
 results=[];lut=[bytes((((v>>s)&31)<<3)|(((v>>s)&31)>>2) for s in [0,5,10]) for v in struct.unpack('<64H',colors())]
 for frame,mode in [(g,0) for g in range(12,21)]+[(12,m) for m in range(1,7)]:
  name=f'frame-{frame}-mode-{mode}'
  (a.out/(name+'.tsv')).write_text('\n'.join(trace[frame])+'\n')
  s=run('vsim',['-c','work.native_planes165_tb',f'+INPUT={name}.tsv',f'+OUTPUT={name}.dump',f'+MODE={mode}',
   '-do','onerror {quit -code 1}; run -all; quit -f'],name)
  info,words=decode(a.out/(name+'.dump'));info.update(frame=frame,mode=mode)
  match=re.search(r'FETCH new=(\d+)/(\w+) old=(\d+)/(\w+)',s);assert match
  info['fetch_errors']=int(match[2],16);info['old_fetch_errors']=int(match[4],16)
  assert info['valid']==(mode==0),info
  if not mode:
   source=[int(w,16) for w in (a.out/(name+'.dump.events')).read_text().split()]
   baseline=[int(w,16) for w in (a.out/(name+'.dump.old')).read_text().split()]
   assert baseline==old[frame],(frame,'old baseline replay differs')
   expected=old[frame]+([pairs[frame]['descriptor']] if frame in pairs else [])
   assert sorted(source)==sorted(expected),(frame,'unexpected changed descriptor')
   assert equivalent(words,source) and len(words)==7401,(frame,'producer reconstruction')
   rows=[rowsets[frame][y] for y in range(224)]
   plan=PlaneConsumer().prepare(words,rows,tiles)
   rgb=reference_planes_rgb(words,rows,tiles)
   pixels=[int(v,16) for v in (a.stream/f'game-{frame}.hex').read_text().split()][8*256:232*256]
   expected=b''.join(lut[v&63] for v in pixels)
   assert rgb==expected,(frame,'actual PPU pixel mismatch',sum(x!=y for x,y in zip(rgb,expected)))
   info.update(events=len(words),mixed=sum(bool(w>>56) for w in words),pixels=57344,derived_patterns=plan['derived_patterns'])
   # Canonical extension, missing tile and budget refusal cannot mutate state.
   c=PlaneConsumer();before=(c.consumer.serial,dict(c.identities),c.consumer.vram)
   bad=list(words);bad[0]|=1<<63
   for bad_words,bad_tiles in [(bad,tiles),(words,{})]:
    try:c.prepare(bad_words,rows,bad_tiles)
    except Unsupported:pass
    else:raise AssertionError('invalid input accepted')
    assert before==(c.consumer.serial,c.identities,c.consumer.vram)
  results.append(info)
 result=dict(passed=True,cases=results,first_pairs=list(pairs.values()),actual_pixels=9*57344,
  public_sources={n:sha(ROOT/n) for n in files+['tools/nes_native_planes165.py','tools/test_nes_native_planes165.py']},
  scope='Same-edge actual-core observations replayed at original intervals, new fetch directly drives bounded compact producer. Not live full-core binding, host CDC, CHR fill, physical resource/FPS proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
