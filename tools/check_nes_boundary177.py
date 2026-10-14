# SPDX-License-Identifier: MIT
"""Gate the output-only observation candidate against exact174 and routed evidence."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_boundary177 import prepare,CHANGED
from decode_nes_boundary177 import sample,report,FLAGS
from check_nes_check165 import inspect
from check_nes_retire165 import nominal
from check_nes_boundary165 import measurements

def decoder_checks():
 base=6<<18
 golden=sample('000000000000000000186000')
 assert golden['export_state']=='HEADER' and golden['owned']
 assert sum(golden[k] for k in FLAGS)==1
 for i,k in enumerate(FLAGS):
  r=sample(f'{base|(1<<(13-i)):024x}')
  assert r[k] and sum(r[x] for x in FLAGS)==1
 for state in range(16):
  r=sample(f'{base|(state<<14):024x}')
  assert not any(r[x] for x in FLAGS)
 for upper in [1,(1<<74)-1,0x123456789abcdef]:
  r=sample(f'{(upper<<22)|base:024x}')
  rebuilt=(r['scanline']<<87)|(r['dot']<<78)|(r['legacy_flags']<<66)|(r['rom_address']<<44)|(r['hint_address']<<22)
  assert rebuilt==upper<<22
 for bad in ['0'*24,'x'*24,'00000000000000000018000']:
  try:sample(bad)
  except ValueError:pass
  else:raise AssertionError(bad)
 text='candidate=NES-GAME-177\nppu_history_kind=LAST16_BOUNDARY177_LOW22\nppu_history_valid=1\nppu_history_count=1\nppu_history_00=000000000000000000186000\n'
 assert report(text)['samples']==[golden]
 for bad in [text.replace('NES-GAME-177','NES-GAME-174'),text.replace('valid=1','valid=0')]:
  try:report(bad)
  except ValueError:pass
  else:raise AssertionError('Accepted invalid report')
 return dict(golden=1,one_hot_flags=14,states=16,upper74=3,negative_samples=3,report_roundtrip=1,negative_reports=2)

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','io','test','reproduce','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();load=lambda p:json.loads(p.read_bytes())
 assert not a.out.exists()
 m=load(a.candidate/'preparation.json');r=prepare(a.baseline,a.reproduce)
 assert m==r and set(m['changed'])==set(CHANGED)
 for n,h in m['sources'].items():
  assert sha(a.candidate/n)==sha(a.reproduce/n)==sha(a.io/n)==h,n
  assert sha(a.baseline/n)==m['baseline'][n],n
  if n not in CHANGED:assert h==m['baseline'][n],n
 # Read-only TimeQuest copy: preserve routed DB except its own timing cache.
 preserved={f.relative_to(a.candidate).as_posix():sha(f) for f in (a.candidate/'db').rglob('*') if f.is_file() and not f.name.endswith('.taw.rdb') and '_io_sim_cache.' not in f.name}
 for n,h in preserved.items():assert sha(a.io/n)==h,n
 assert sha(a.io/'nes_boundary165_paths.tcl')==sha(ROOT/'tools/nes_boundary165_paths.tcl')
 t=load(a.test/'result.json');assert t['passed'] and len(t['release_cases'])==14
 assert t['sources']==m['sources']
 public={**m['public_sources'],**t['public_sources']}
 for n,h in public.items():assert sha(ROOT/n)==h,n
 for n in ['tools/check_nes_boundary177.py','tools/decode_nes_boundary177.py','tools/check_nes_check165.py','tools/check_nes_retire165.py','tools/check_nes_boundary165.py','tools/nes_boundary165_paths.tcl']:public[n]=sha(ROOT/n)
 f=inspect(a.candidate);nm=nominal(a.candidate);io=measurements(a.io)
 assert f['fit_pass'] and nm['passed'] and io['conditional_data_bounds_pass'] and io['native_payload_reset_pass']
 result=dict(passed=True,functional_passed=True,fit=f,nominal=nm,io=io,sources=m['sources'],public_sources=public,
  decoder=decoder_checks(),functional=t,source_byte_reproduction=True,unchanged_files=len(m['sources'])-2,
  preserved_routed_db_files=len(preserved),datapath_control_changed=False,history_upper74_unchanged=True,
  hardware_pending=True,video_fix_proven=False,fps60_proven=False,full_io_signoff=False)
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(passed=True,unchanged_files=result['unchanged_files'],setup=nm['worst_setup']['slack'],le=f['fit_le'],io=io['conditional_data_bounds_pass'])))
if __name__=='__main__':main()
