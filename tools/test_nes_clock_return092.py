# SPDX-License-Identifier: MIT
"""Test parser092 against received bytes, both hex cases, and semantic corruption."""
from pathlib import Path
import argparse,json,hashlib,re,subprocess,sys
from check_nes_clock_report092 import check
def main():
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 raw=a.report.read_bytes();assert len(raw)==1099 and hashlib.sha256(raw).hexdigest()=='5ba647a785c5c35b82ae0acc09f08498b6d30c47277239d118d43e41c7cd29de'
 received=a.out/'HW090000.TXT';received.write_bytes(raw)
 old=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('check_nes_clock_report090.py')),str(received)],capture_output=True)
 (a.out/'old-parser.log').write_bytes(old.stdout+old.stderr);assert old.returncode!=0 and b'AssertionError' in old.stderr
 parsed=check(received);assert parsed['result']=='CLOCK ACTIVE' and parsed['captured']==2
 assert [(r['sequence'],r['count'],r['flags']) for r in parsed['snapshots']]==[(0,0,6),(2,1342354,7),(3,1342354,7)]
 text=raw.decode('ascii');variants=[]
 for label,upper in [('uppercase',True),('lowercase',False)]:
  value=re.sub(r'(?<=RAW:)([^\n]+)',lambda m:m[0].upper() if upper else m[0].lower(),text)
  f=a.out/(label+'.txt');f.write_bytes(value.encode());r=check(f);r['file']=parsed['file'];assert r==parsed;variants.append(label)
 for name,value in [('count',text.replace('COUNT: 1342354','COUNT: 1342355',1)),('raw',text.replace('92 7b 14','93 7b 14',1)),('label',text.replace('RESULT: CLOCK ACTIVE','RESULT: CLOCK ABSENT',1)),('invalidhex',text.replace('92 7b 14','92 gb 14',1))]:
  f=a.out/(name+'.txt');f.write_bytes(value.encode())
  try:check(f)
  except AssertionError:pass
  else:raise AssertionError(name)
 result=dict(original_bytes=len(raw),original_sha256=hashlib.sha256(raw).hexdigest(),parsed=parsed,valid_cases=3,corruption_rejections=4,old_case_only_rejection=True,original_unchanged=a.report.read_bytes()==raw)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
