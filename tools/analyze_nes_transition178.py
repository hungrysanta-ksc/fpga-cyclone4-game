# SPDX-License-Identifier: MIT
"""Summarize START scene evidence without equating collector output with FPS."""
from pathlib import Path
import argparse,json,hashlib

def analyze(path):
 def states(name):
  rows=[]
  for line in (path/name).read_text().splitlines():
   p=line.split();e=int(p[3],16)
   rows.append(dict(generation=int(p[0]),frame=int(p[1]),valid=bool(int(p[2])),errors=f'{e:07x}',fetch_error=e&255,compact_error=(e>>8)&255,raster_error=(e>>16)&255,
    scroll_seen=int(p[4]),rows=int(p[5]),groups=int(p[6]),objects=int(p[7]),exceptions=int(p[8]),palettes=int(p[9])))
  runs=[]
  for r in rows:
   key=(r['valid'],r['errors'])
   if runs and runs[-1]['key']==key:runs[-1]['last_frame']=r['frame'];runs[-1]['count']+=1
   else:runs.append(dict(key=key,first_frame=r['frame'],last_frame=r['frame'],count=1))
  return dict(rows=rows,runs=runs,
   maxima={n:max((r[n] for r in rows),default=0) for n in ['rows','groups','objects','exceptions','palettes']},
   rejected_frames_by_owner={name:sum(not r['valid'] and r[key]!=0 for r in rows)
    for name,key in [('fetch','fetch_error'),('compact','compact_error'),('raster','raster_error')]})
 pads=[];last=None
 for line in (path/'pad.tsv').read_text().splitlines():
  f,t,b=line.split()
  if b!=last:pads.append(dict(frame=int(f),ticks=int(t),buttons=b));last=b
 scenes=[x.split() for x in (path/'scene.tsv').read_text().splitlines()]
 masks=[];last=None
 for row in scenes:
  if row[1]!=last:masks.append(dict(frame=int(row[0]),mask=row[1]));last=row[1]
 return dict(immediate=states('states.tsv'),held10=states('slow-states.tsv'),input_changes=pads,end_of_frame_mask_changes=masks,
  completed=(path/'result.json').exists(),scope='End-of-frame mask omits midline changes; states record sealed collectors, not delivered pictures. Actual ideal-ROM game input; not physical root-cause proof.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('path',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();r=analyze(a.path)
 if a.out:
  assert not a.out.exists();a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
 print(json.dumps({k:({n:v for n,v in x.items() if n!='rows'} if isinstance(x,dict) else x) for k,x in r.items()},indent=2))
