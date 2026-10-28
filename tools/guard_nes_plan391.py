# SPDX-License-Identifier: MIT
"""Actual65816 negative compact-plan/coverage/STOP and high-token guards."""
import argparse,inspect,json,struct
import probe_nes_plan391 as candidate
from nes_delta231 import sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();root=candidate.Path(a.out);root.mkdir(parents=True,exist_ok=False);rows=[]
 cases=('magic','version','bank','generation','length','range_count','word_count','sparse_start','sparse_span','column_hole','map_end','missing','beforeflushSTOP','gatherSTOP','displaySTOP','high_token','dense','duplicate','reversed_column')
 for name in cases:
  frame=908 if name in ('column_hole','gatherSTOP','reversed_column')else 907
  jobs=candidate.fixtures(frame);meta=next(j for j in jobs if not j['typed']and bytes.fromhex(j['descriptor'])[1]==6);b=bytearray.fromhex(meta['data']);m=next(j for j in jobs if j['typed']and bytes.fromhex(j['descriptor'])[0]&2)
  if name in ('magic','version','bank','generation','range_count','word_count'):b[{'magic':0,'version':2,'bank':4,'generation':6,'range_count':12,'word_count':14}[name]]^=1
  elif name=='length':
   desc=bytearray.fromhex(meta['descriptor']);desc[4:6]=struct.pack('<H',len(b)-1);meta['descriptor']=desc.hex();b=b[:-1]
  elif name=='sparse_start':b[16]^=1
  elif name=='sparse_span':b[18]^=1
  elif name=='column_hole':b[16:]=bytes([32,0])*64
  elif name=='reversed_column':
   i=next(i for i in range(16,144,2)if b[i]<32);b[i:i+2]=bytes([31,0])
  elif name=='dense':
   b=b[:16];b[3]=2;desc=bytearray.fromhex(meta['descriptor']);desc[4:6]=struct.pack('<H',16);meta['descriptor']=desc.hex()
  elif name=='map_end':
   desc=bytearray.fromhex(m['descriptor']);desc[3:5]=struct.pack('<H',2048);m['descriptor']=desc.hex()
  elif name=='missing':jobs.remove(meta)
  meta['data']=b.hex()
  if name=='duplicate':jobs.insert(jobs.index(meta)+1,dict(meta))
  if name=='high_token':
   for j in jobs:
    j['token']+=0x70000000
    if j['typed']:
     desc=bytearray.fromhex(j['descriptor']);desc[7:11]=struct.pack('<I',j['token']);j['descriptor']=desc.hex()
  lua=candidate.LUA
  normal=name in ('high_token','dense')
  if not normal:
   condition='staged>=#JOBS'if name=='beforeflushSTOP'else'stop391'if name in ('gatherSTOP','displaySTOP')else'false'
   lua=lua.replace('STOP and staged>=1','STOP and ('+condition+')')
   lua=lua.replace('assert(STOP and v==0xee and not ppu_start and staged==1);',"assert(STOP and v==0xee and emu.read(0xf080,emu.memType.snesWorkRam)==0);")
   lua=lua.replace("local at=1;local reads=0;","local stop391=false;local at=1;local reads=0;")
   if name in ('gatherSTOP','displaySTOP'):
    label='gather386'if name=='gatherSTOP'else'display383'
    lua+='\nemu.addMemoryCallback(function()stop391=true end,emu.callbackType.exec,LABELS.'+label+')\n'
  # Reuse the real driver and independent whole-image assertions. STOP cases
  # may terminate after PPU begins;their ACK still must remain absent.
  source=inspect.getsource(candidate.old.main)
  source=source.replace("p.add_argument('--frames',default='907,908,909,910,911,912,913,914,915,916')", "p.add_argument('--frames',default='"+str(frame)+"')")
  source=source.replace("[(f,False) for f in map(int,a.frames.split(','))]+[(907,True)]", "[("+str(frame)+","+str(not normal)+")]")
  source=source.replace("('EXPECTOAM',expected[4608:5152])", "('EXPECTOAM',expected[4608:5152]),('INITHDMA',prior[5152:8570]),('EXPECTHDMA',expected[5152:8570])")
  ns=dict(candidate.old.__dict__,rom=candidate.rom,fixtures=lambda f:jobs,LUA=lua,__file__=__file__)
  import sys
  saved=sys.argv;sys.argv=[__file__,'--out',str(root/name)]
  try:exec(compile(source,'guard391-driver','exec'),ns);ns['main']()
  finally:sys.argv=saved
  report=json.loads((root/name/'result.json').read_text());r=report['cases'][0];assert r['passed'];rows.append(dict(name=name,result=r))
 (root/'result.json').write_text(json.dumps(dict(passed=True,cases=rows,source=sha(candidate.Path(__file__))),indent=2)+'\n')
if __name__=='__main__':main()
