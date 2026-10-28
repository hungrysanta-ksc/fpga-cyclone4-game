# SPDX-License-Identifier: MIT
"""Select measured native phase envelopes without adding HDMA twice.
Each selected job/view/tail is an intact native interval. Mixing worst observed
intervals is a service allocation, not a physical CPU phase/WCET proof.
"""
import argparse,csv,json,struct
from pathlib import Path
from nes_delta231 import BASE,sha

def load(q,f):
 d=q/str(f);events=[list(map(int,r))for r in csv.reader((d/'events.csv').read_text().splitlines())]
 jobs=json.loads((d/'fixture.json').read_text());fixture=json.loads((d/'fixture401.json').read_text());hdma=json.loads((d/'hdma-result401.json').read_text())
 assert json.loads((d/'cpu-result.json').read_text())['passed']
 begin=hdma['fixture_begin'];end=hdma['fixture_end'];extra=end-begin-44
 assert extra>=0
 if fixture['fixture_bytes']:
  events=[r[:4]+[r[4]-extra]+r[5:]if r[4]>=end else r for r in events if not begin<=r[4]<end]
 else:assert extra==0
 assert fixture['kernel_SHA']==sha(BASE/'probes/nes-joint400/native01'/str(f)/'spool.sfc')
 if f>=907:assert hdma['reads']>0 and hdma['writes']>0 and hdma['prior_RAM_exact']
 first={i:next(r[4]for r in events if r[0]==i and r[1:3]==[0,0x6001])for i in range(1,len(jobs)+2)}
 ends={i:next(r[4]for r in events if r[0]==i and r[1:4]==[1,0x6050,0xa5])for i in range(1,len(jobs)+1)}
 source=[]
 for i in range(1,len(jobs)+1):
  origin=ends[i-1]if i>1 else first[1]
  ev=[r for r in events if first[i]<=r[4]<=ends[i]]
  assert ev[-1][1:4]==[1,0x6050,0xa5]
  source.append(dict(origin=origin,events=ev,clocks=ends[i]-origin))
 last_view=max(r[4]for r in events if r[1]==0 and 0x6070<=r[2]<=0x607b)
 first_poll=next(r[4]for r in events if r[1:3]==[0,0x4212]and r[4]>last_view)
 head_end=first_poll if f>=907 else last_view
 head=[r for r in events if ends[len(jobs)]<r[4]<=head_end]
 assert [r[2]for r in head if r[1]==0 and 0x6070<=r[2]<=0x607b]==list(range(0x6070,0x607c))
 tm=list(csv.DictReader((d/'timings.csv').read_text().splitlines()))
 pp=next(int(r['clock'])for r in tm if r['phase']=='PPU_trigger')-extra;last_pp=max(int(r['clock'])for r in tm if r['phase']=='PPU_done')-extra
 origin=max(r[4]for r in events if r[1:3]==[0,0x4212]and r[4]<pp)if f>=907 else last_view
 tail=[r for r in events if r[4]>origin];split=0
 if f<907:
  after=max(r[4]for r in events if r[1:3]==[0,0x4212]and r[4]<events[-1][4])
  tail=[r for r in events if origin<r[4]<=last_pp]+[r[:4]+[last_pp+r[4]-after]+r[5:]for r in events if r[4]>after];split=sum(r[4]<=last_pp for r in tail)
 polls=[r[4]for r in events if r[1:3]==[0,0x4212]and first_poll<=r[4]<=origin]
 return dict(path=d,phase=fixture['phase_line'],events=events,jobs=jobs,source=source,head=dict(origin=ends[len(jobs)],events=head,clocks=head_end-ends[len(jobs)]),tail=dict(origin=origin,events=tail,clocks=tail[-1][4]-origin),split=split,poll_clocks=max([92]+[b-a for a,b in zip(polls,polls[1:])]),hdma=hdma,excluded_prior_setup_clocks=extra)

def main():
 p=argparse.ArgumentParser();p.add_argument('--native',nargs='+',type=Path,required=True);p.add_argument('--control',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.out.resolve();root.mkdir(parents=True,exist_ok=False);report=[]
 control=json.loads((a.control/'907/hdma-result401.json').read_text());assert control['fixture_end']-control['fixture_begin']==44 and control['reads']==control['writes']==0
 for f in range(905,917):
  samples=[load(q,f)for q in a.native if(q/str(f)).is_dir()];assert samples
  jobs=samples[0]['jobs'];assert all(s['jobs']==jobs for s in samples)
  d=root/str(f);d.mkdir()
  def save(name,values,width=16):(d/name).write_text('\n'.join(f'{v:0{width}x}'for v in values)+'\n',newline='\n')
  def packed(ev,origin):return[((r[4]-origin)<<40)|(r[1]<<32)|(r[2]<<8)|r[3]for r in ev]
  source=[];selected=[];data=bytearray();desc=bytearray()
  for i,j in enumerate(jobs):
   s=max(samples,key=lambda s:s['source'][i]['clocks']);part=s['source'][i];source +=[len(part['events'])]+packed(part['events'],part['origin']);selected.append(dict(job=i+1,phase=s['phase'],clocks=part['clocks']))
   b=bytes.fromhex(j['data']);data+=b;desc+=bytes.fromhex(j['record'])+struct.pack('<HHB',j['offset'],len(b),int(j['first'])+2*int(j['last']))
  source.append(0);head_sample=max(samples,key=lambda s:s['head']['clocks']);h=head_sample['head'];tail_sample=max(samples,key=lambda s:s['tail']['clocks']);t=tail_sample['tail']
  body=3840
  for j in jobs:
   r=bytes.fromhex(j['record'])
   if j['first']and r[6]&3!=3:body+=8*int.from_bytes(r[4:6],'little')+(1200 if r[6]&3==0 else 1408)
  cutoff=246 if body<20001 else 238 if body<30001 else 230 if body<40001 else 225
  cfg=[0,0,t['clocks']+512,len(t['events']),cutoff,tail_sample['split'],len(jobs)]
  for name,values,width in(('source',source,16),('data',data,2),('desc',desc,2),('tail',[len(t['events'])]+packed(t['events'],t['origin']),16),('config',cfg,16)):
   save(f'jobs394-{name}{f}.hex',values,width)
  # The source image contains only current-view bytes, not previous fixtures.
  from probe_nes_jobs394_native import current_view
  save(f'jobs394-view{f}.hex',current_view(f),2);save(f'view401-{f}.hex',[len(h['events'])]+packed(h['events'],h['origin']));save(f'poll401-{f}.hex',[max(s['poll_clocks']for s in samples)])
  row=dict(frame=f,source_jobs=selected,source_service_clocks=sum(r['clocks']for r in selected),head_phase=head_sample['phase'],head_clocks=h['clocks'],tail_phase=tail_sample['phase'],tail_clocks=t['clocks'],poll_clocks=max(s['poll_clocks']for s in samples),config=cfg,samples=[dict(phase=s['phase'],HDMA=s['hdma'],excluded_prior_setup_clocks=s['excluded_prior_setup_clocks'],kernel=sha(s['path']/'kernel400.sfc'),ROM=sha(s['path']/'spool.sfc'),events=sha(s['path']/'events.csv'),fixture=sha(s['path']/'fixture401.json'))for s in samples],files={q.name:sha(q)for q in d.iterdir()})
  (d/'model401.json').write_text(json.dumps(row,indent=2)+'\n');report.append(row)
 (root/'result.json').write_text(json.dumps(dict(passed=True,frames=12,phase_samples=[0,112,224],scope=__doc__,cases=report),indent=2)+'\n');print(json.dumps([dict(frame=r['frame'],source_clocks=r['source_service_clocks'],head_clocks=r['head_clocks'],poll_clocks=r['poll_clocks'])for r in report]))
if __name__=='__main__':main()
