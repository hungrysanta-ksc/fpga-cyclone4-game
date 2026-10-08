# SPDX-License-Identifier: MIT
"""Check received090 TXT with either hex case; preserve original bytes."""
import argparse,json,re
from pathlib import Path
def check(path):
 raw=path.read_bytes();assert 600<len(raw)<3072 and b'\x00' not in raw
 text=raw.decode('ascii');assert text.startswith('CLOCKREPORT090 / FPGA CF87 / MCU CONFIG089 READER088\n')
 label=re.search(r'^RESULT: (CLOCK ACTIVE|CLOCK ABSENT|CLOCK UNSTABLE|NO CLOCK PROGRESS)$',text,re.M);assert label
 captured=int(re.search(r'CAPTURED_WINDOWS: (\d+)',text)[1]);assert captured in [0,1,2]
 pat=r'(INITIAL0|SAMPLE1|SAMPLE2) RAW:((?: [0-9A-Fa-f]{2}){16})\n  SEQUENCE: (\d+); COUNT: (\d+); WINDOW: (\d+); DIVISOR: (\d+)\n  FLAGS: ([0-9A-Fa-f]{2}); VALID: (\d); LIVE: (\d); EVER_GAP: (\d); LAST_GAP: (\d)'
 rows=re.findall(pat,text);assert len(rows)==3;decoded=[]
 for i,row in enumerate(rows):
  assert row[0]==['INITIAL0','SAMPLE1','SAMPLE2'][i]
  data=bytes.fromhex(row[1]);fields=[int.from_bytes(data[j:j+4],'little') for j in [2,6,10]]+[data[14]]
  assert fields==list(map(int,row[2:6]))
  assert int(row[6],16)==data[1] and list(map(int,row[7:]))==[(data[1]>>j)&1 for j in range(4)]
  if i>captured:assert not any(data)
  elif i==0 and not any(data):assert label[1]=='NO CLOCK PROGRESS' and captured==0
  else:assert data[0]==0x87 and fields[2:]==[8000000,16] and data[15]==0
  decoded.append(dict(raw=data.hex(),sequence=fields[0],count=fields[1],flags=data[1]))
 if label[1]!='NO CLOCK PROGRESS':assert captured==2
 if label[1]=='CLOCK ACTIVE':assert all(r['count']>0 and r['flags']&3==3 and not r['flags']&8 for r in decoded[1:])
 if label[1]=='CLOCK ABSENT':assert all(r['count']==0 and not r['flags']&2 for r in decoded[1:])
 assert 'FILE ALONE DOES NOT PROVE SAVE SUCCESS' in text
 return dict(file=path.name,result=label[1],captured=captured,snapshots=decoded,physical_save_proven=False)
def main():
 p=argparse.ArgumentParser();p.add_argument('files',type=Path,nargs='+');a=p.parse_args();print(json.dumps([check(f) for f in a.files],indent=2))
if __name__=='__main__':main()
