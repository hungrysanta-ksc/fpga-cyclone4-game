# SPDX-License-Identifier: MIT
"""Independent parser checks, including incomplete initial snapshot and corruption."""
from pathlib import Path
import argparse,json,re
from check_nes_clock_report090 import check
def main():
 p=argparse.ArgumentParser();p.add_argument('--reports',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
 files=sorted(a.reports.glob('saved-*.txt'));assert len(files)==16
 results=[check(f) for f in files];source=next(f for f in files if 'mode0' in f.name).read_text()
 changes=[('count',source.replace('COUNT: 1250000','COUNT: 1250001',1)),('raw',source.replace('87 07 02','86 07 02',1)),('result',source.replace('RESULT: CLOCK ACTIVE','RESULT: CLOCK ABSENT',1)),('truncated',source[:500])]
 for name,text in changes:
  f=a.out/(name+'.txt');f.write_text(text,encoding='ascii',newline='\n')
  try:check(f)
  except (AssertionError,AttributeError,TypeError):pass
  else:raise AssertionError(name)
 text=next(f for f in files if 'mode3' in f.name).read_text()
 text=re.sub(r'INITIAL0 RAW:.*?\n  FLAGS:.*?\n','INITIAL0 RAW:'+(' 00'*16)+'\n  SEQUENCE: 0; COUNT: 0; WINDOW: 0; DIVISOR: 0\n  FLAGS: 00; VALID: 0; LIVE: 0; EVER_GAP: 0; LAST_GAP: 0\n',text,flags=re.S)
 f=a.out/'no-initial-snapshot.txt';f.write_text(text,encoding='ascii',newline='\n');check(f)
 result=dict(valid_saved_reports=16,corruption_rejections=4,missing_initial_snapshot=1,physical=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
