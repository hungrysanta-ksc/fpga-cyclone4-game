# SPDX-License-Identifier: MIT
"""Join completed normal tests, corrected STOP-only fixture and max-size test.
Preserve old failure snapshots; do not rerun already passed normal cases.
"""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['normal','stop','maximum','video','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 stop=json.loads((a.stop/'result.json').read_bytes());maximum=json.loads((a.maximum/'result.json').read_bytes());assert stop['passed'] and maximum['passed']
 # Only old, unreachable-in-normal-mode STOP expectation was removed from C.
 old=(a.normal/'producer169.c').read_text();new=(a.stop/'producer169.c').read_text()
 assert old.replace(' if(!strcmp(mode,"stop")&&gen==15){assert(!ok&&s.state==NES_SINK165_FAULT&&s.displayed);return;}','')==new
 for path in [a.normal,a.stop,a.maximum]:
  assert (path/'client/sink-program.hex').read_bytes()==(a.stop/'client/sink-program.hex').read_bytes()
  for n in ['nes_native_sink165.c','nes_sink_trace168.c']:
   assert (path/n).read_bytes()==(a.stop/n).read_bytes()
 for q in [stop,maximum]:
  for n,h in q['public_sources'].items():assert sha(ROOT/n)==h,n
 cases=[]
 for mode in ['overflow','budget']:
  d=a.normal/mode;q=json.loads((d/'consumer-result.json').read_bytes());assert q['passed'] and q['commits']==6 and q['fallback_chunks']==6 and q['old_frames_held']>=6
  for i in range(1,7):assert (d/f'frame-{i}.rgb').read_bytes()==(a.normal/(mode+'-reference')/f'frame-{i}.rgb').read_bytes()
  for i in range(1,4):assert (d/f'frame-{i}.rgb').read_bytes()==(a.video/f'expected-{min(i,2)}.rgb').read_bytes()
  cases.append(q|{'mode':mode,'executed_directory':str(d),'reference':False})
 sq=stop['cases'][0];assert sq['commits']==3 and sq['fallback_chunks']==1;cases.append(sq)
 mq=next(q for q in maximum['cases'] if not q['reference']);assert mq['commits']==6 and mq['fallback_chunks']==9;cases.append(mq|{'mode':'maximum'})
 a.out.mkdir(parents=True)
 for f in a.stop.glob('*.c'):shutil.copyfile(f,a.out/f.name)
 shutil.copytree(a.stop/'client',a.out/'client')
 sources=set(stop['public_sources'])|set(maximum['public_sources'])|{'tools/verify_nes_banked169.py'}
 snapshots={}
 for label,path in [('normal03',a.normal),('stop04',a.stop),('maximum01',a.maximum)]:
  snapshots[label]={f.relative_to(path).as_posix():sha(f) for f in path.rglob('*') if f.is_file()}
 result=dict(passed=True,client=stop['client'],cases=cases,pixel_comparisons=sum(q['commits'] for q in cases)*256*239,public_sources={n:sha(ROOT/n) for n in sorted(sources)},executed_snapshots=snapshots,source_correction='normal03 completed four cases; old gen15 STOP-only assertion corrected and only STOP rerun as stop04. Production SNES/MCU bytes identical across tests. Test02 pixel oracle invalid: changed unloaded tile indexes; test03 preserves tile indexes.',scope='Actual65816/C file mailbox; E2/E3, max6 chunks, atomic held old frames, final pixel oracle, reverse slot/noop, STOP. No hardware/FPS claim.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS169 joined',result['pixel_comparisons'])
if __name__=='__main__':main()
