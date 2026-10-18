# SPDX-License-Identifier: MIT
"""Partition exact-mask runtime by disjoint instruction-boundary intervals."""
from pathlib import Path
import argparse,csv,json,shutil
from nes_delta231 import sha

EVENTS=('mask_record247','profile_copy247','profile_copied247','profile_append247','profile_appended247','profile_service247','profile_serviced247')
PARTS=('prepare','copy','address','append','guard','service')


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('test','client','baseline','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 for n in ('body.bin','sink-program.hex','sink165.sfc'):assert (a.client/n).read_bytes()==(a.baseline/n).read_bytes()
 test=json.loads((a.test/'result.json').read_text());assert test['passed'] and test['commits']==71
 details=list(csv.DictReader((a.test/'run/mask-detail247.csv').open()));assert len(details)%7==0
 rows={g:dict(frame=g+904,records=0,words=0,**{k+'_clocks':0 for k in PARTS}) for g in range(1,72)};records=[];last={};maxgap=0
 for i in range(0,len(details),7):
  d=details[i:i+7];assert tuple(x['event'] for x in d)==EVENTS
  g=int(d[0]['generation']);ordinal=int(d[0]['ordinal']);assert all(int(x['generation'])==g and int(x['ordinal'])==ordinal for x in d)
  times=[int(x['clock']) for x in d];assert times==sorted(times)
  cursor=int(d[0]['cursor']);q=(a.test/f'run/req-{ordinal:04d}.bin').read_bytes();mask=q[16+cursor+1];group=q[16+cursor];words=mask.bit_count()
  assert int(d[1]['mask'])==mask and int(d[1]['group'])==group and int(d[-1]['cursor'])==cursor+2+2*words
  v=dict(frame=g+904,ordinal=ordinal,group=group,mask=mask,words=words)
  for k,t0,t1 in zip(PARTS,times,times[1:]):v[k+'_clocks']=t1-t0;rows[g][k+'_clocks']+=t1-t0
  rows[g]['records']+=1;rows[g]['words']+=words;records.append(v)
  if (g,ordinal) in last:maxgap=max(maxgap,times[-1]-last[g,ordinal])
  last[g,ordinal]=times[-1]
 phase={};active={}
 for x in csv.DictReader((a.test/'run/mask-phase247.csv').open()):
  g=int(x['generation']);t=int(x['master_clock'])
  if x['event']=='mask247':assert g not in active;active[g]=t
  elif x['event']=='mask_return247':phase[g]=phase.get(g,0)+t-active.pop(g)
 assert not active
 for g,row in rows.items():
  row['total_clocks']=phase[g];row['other_clocks']=phase[g]-sum(row[k+'_clocks'] for k in PARTS);assert row['other_clocks']>=0
  for k in (*PARTS,'other','total'):row[k+'_ms']=row[k+'_clocks']/21477.270
 warm=list(rows.values())[2:];total=sum(x['total_clocks'] for x in warm)
 stats={k:dict(total_clocks=sum(x[k+'_clocks'] for x in warm),total_ms=sum(x[k+'_ms'] for x in warm),share_percent=100*sum(x[k+'_clocks'] for x in warm)/total,max_frame_ms=max(x[k+'_ms'] for x in warm)) for k in (*PARTS,'other','total')}
 result=dict(passed=True,scope=__doc__,byte_exact=True,frames=71,records=len(records),warm_records=sum(x['records'] for x in warm),warm_words=sum(x['words'] for x in warm),parts=stats,max_within_packet_service_return_gap_clocks=maxgap,max_within_packet_service_return_gap_ms=maxgap/21477.270,scope_service_gap='Observed consecutive group service returns within mask packets only;not global STOP deadline.',input_hashes={n:sha(f) for n,f in [('test',a.test/'result.json'),('client',a.client/'result.json'),('baseline',a.baseline/'result.json'),('details',a.test/'run/mask-detail247.csv'),('phase',a.test/'run/mask-phase247.csv')]},script_sha256=sha(Path(__file__)),physical=False)
 for name,items in [('frames',list(rows.values())),('records',records)]:
  with (a.out/(name+'.csv')).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=items[0],lineterminator='\n');w.writeheader();w.writerows(items)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');shutil.copyfile(__file__,a.out/'analyzer.py');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
