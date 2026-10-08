# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil
from nes_pair105 import verify,digest,POLICY

def main():
 p=argparse.ArgumentParser()
 for n in ['review','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 mh=digest((a.review/'manifest.json').read_bytes());base=json.loads((a.review/'manifest.json').read_bytes())
 rows=[]
 def run(name,edit=None,message=None,rehash=False):
  d=a.out/name;shutil.copytree(a.review,d);edit and edit(d)
  h=digest((d/'manifest.json').read_bytes()) if rehash else mh
  try:
   result=verify(d,h)
  except ValueError as err:
   if not message or message not in str(err):raise
   rows.append(dict(name=name,rejected=True,reason=str(err)))
  else:
   if message:raise AssertionError('fault accepted: '+name)
   assert result['pair_identity_pass'] and result['policy']==POLICY
   rows.append(dict(name=name,rejected=False,result=result))
 def change_manifest(d,fn):
  m=json.loads((d/'manifest.json').read_bytes());fn(m);(d/'manifest.json').write_text(json.dumps(m)+'\n')
 run('normal')
 for i,n in enumerate(base['files']):
  def corrupt(d,n=n):
   f=d/'files'/n;b=bytearray(f.read_bytes())
   if b:b[len(b)//2]^=1
   else:b.append(1)
   f.write_bytes(b)
  run('corrupt-'+str(i),corrupt,'file mismatch')
 run('missing',lambda d:(d/'files/arm104.stm').unlink(),'unexpected or missing')
 run('extra',lambda d:(d/'files/old071.stm').write_bytes(b'old'),'unexpected or missing')
 run('swap-firmware',lambda d:(d/'files/arm104.stm').write_bytes((d/'files/restore044.stm').read_bytes()),'file mismatch')
 run('stale-digest',lambda d:change_manifest(d,lambda m:m.update(candidate='old')),'manifest digest differs')
 run('wrong-role',lambda d:change_manifest(d,lambda m:m['files']['restore044.stm'].update(role='diagnostic-firmware')),'identity/role/policy',True)
 run('old-marker',lambda d:change_manifest(d,lambda m:m['files']['marker0.empty'].update(sd_target='NES VERIFY 069 80.nh1')),'identity/role/policy',True)
 for flag in POLICY:
  run('approve-'+flag,lambda d,f=flag:change_manifest(d,lambda m:m['policy'].update({f:True})),'identity/role/policy',True)
 (a.out/'result.json').write_text(json.dumps(dict(cases=rows,normal=1,rejected=len(rows)-1,physical=False,installable=False),indent=2)+'\n')
 shutil.copy2(__file__,a.out/'executed-test105.py');print('PASS105 pair identity normal=1 rejected='+str(len(rows)-1))
if __name__=='__main__':main()
