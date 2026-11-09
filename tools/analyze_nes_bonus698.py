# SPDX-License-Identifier: MIT
"""Check hardware-identical boundary signatures and retain private reproduction evidence."""
from pathlib import Path
import argparse,json,re,shutil,zipfile
from nes_game147 import ROOT,ROM_SHA,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--temp',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();assert not a.out.exists();a.out.mkdir(parents=True)
 ref=a.temp/'nes-bonus698-reference06';meta=json.loads((ref/'result.json').read_bytes())
 assert meta['rom_sha256']==ROM_SHA
 for n,h in meta['files'].items():assert sha(ref/n)==h,n
 for n in ['writes.tsv','frame-349.png','frame-355.png','frame-540.png','frame-650.png','frame-680.png']:
  assert (ref/n).read_bytes()==(a.temp/'nes-bonus698-reference05'/n).read_bytes(),n
 assert (ref/'intervention.txt').read_text().startswith('frame350 RAM0075 40 ->60; RAM0079 20 ->80; one shot')
 states=dict(line.strip().split('=',1) for line in (ref/'bank-edge-state.txt').read_text().splitlines())
 assert [int(states[f'ppu.secondarySpriteRam{i}']) for i in range(4)]==[248,255,255,255]
 assert (states['ppu.scanline'],states['ppu.cycle'],states['ppu.control.largeSprites'])==('192','261','true')
 writes=[(int(f),int(y),int(x),int(addr,16),int(v,16)) for f,y,x,addr,v in map(str.split,(ref/'writes.tsv').read_text().splitlines())]
 sel=0;late=[]
 for q in writes:
  if q[3]==0x8000:sel=q[4]
  elif q[3]==0x8001 and sel&7==5 and q[4]==126 and q[1]==192:late.append(q)
 assert (588,192,261,0x8001,0x7e) in late
 expected_context='e200c3f7ce21fbe7';expected_ppu='604198007f9f9f9c'
 hardware=(ROOT/'analysis/hardware697-mmc695-696.json').read_text()
 assert expected_context in hardware
 runs=[];inputs={};private=[]
 for i,phase in [(1,3.5),(2,0),(3,5.5)]:
  d=a.temp/f'nes-bonus698-boundary{i:02d}';m=json.loads((d/'inputs.json').read_bytes());t=(d/'simulation.log').read_text()
  assert 'DONE698 boundary STOP and independent bytes' in t and '# Errors: 0,' in t
  cases=[]
  for row in re.findall(r'CASE698 scenario=(\d+) failed=(\d+) error=(\d+) context=([0-9a-f]+) ppu=([0-9a-f]+) reads=(\d+) checked=(\d+)',t):
   n,failed,error,c,ppu,reads,checked=row;n=int(n)
   assert int(failed)==int(2<=n<=5)
   if 2<=n<=5:assert (int(error),c,ppu,int(reads),int(checked))==(2,expected_context,expected_ppu,2,0)
   else:assert int(error)==0 and int(checked)==1
   cases.append(dict(case=n,failed=bool(int(failed)),error=int(error),context=c,ppu=ppu,reads=int(reads),independent_bytes_checked=int(checked)))
  assert [q['case'] for q in cases]==list(range(8))
  for n,h in m['sources'].items():
   assert sha(d/n)==h,n
   if n!='game147_tb.sv':assert sha(Path(m['board'])/n)==h,n
   if i==1:private.append((d/n,'selected-source/'+n));inputs[n]=h
  for n in ['inputs.json','result.json','simulation.log','game147_tb.sv','run.ps1']:
   if (d/n).exists():private.append((d/n,d.name+'/'+n))
  runs.append(dict(memory_phase_ns=phase,cases=cases,log_sha256=sha(d/'simulation.log')))
 for q in ref.iterdir():
  if q.is_file():private.append((q,'reference06/'+q.name))
 failures={'core01':'testbench declaration/port parse compile failure','core02':'missing Altera RAM simulation library',
  'core03':'author stopped six-frame full boot for excessive runtime; EOF/license-process messages are termination consequence',
  'reference01':'no NES controller configured; title only, not a scene pass','reference02':'same input configuration failure',
  'reference03':'test-runner CLI setting insufficient; title only','reference04':'private runtime copy omitted shared .NET runtime'}
 for name,why in failures.items():
  d=a.temp/('nes-bonus698-'+name)
  for n in ['mesen.log','simulation.log','vlog.log','result.json','intervention.txt','scene.tsv']:
   if (d/n).exists():private.append((d/n,'failed/'+name+'/'+n))
 for n in ['nes-bonus698-entry.mst','nes-bonus698-world1.mst']:
  if (a.temp/n).exists():private.append((a.temp/n,'interactive/'+n))
 for n in ['probe_nes_bonus698.py','probe_nes_bonus698_reference.py','probe_nes_bonus698_boundary.py','analyze_nes_bonus698.py']:
  private.append((ROOT/'tools'/n,'tools/'+n))
 manifest={dst:sha(src) for src,dst in private}
 with zipfile.ZipFile(a.out/'evidence.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for src,dst in private:z.write(src,dst)
  z.writestr('manifest.json',json.dumps(manifest,indent=2)+'\n')
 with zipfile.ZipFile(a.out/'evidence.zip') as z:
  import hashlib
  for n,h in manifest.items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 result=dict(stage=698,rom_sha256=ROM_SHA,production_modified=False,full_game_RTL_replay=False,
  reference=dict(frames=680,repeated_trace_and_five_images_exact=True,entry_map_ram={'0075':['40','60'],'0079':['20','80']},one_shot_frame=350,
   no_intervention_after=350,normal_A_frames=[[360,365],[550,555]],visual_scene='World1 spade roulette',
   CHR5_bank126_writes_line192=len(late),latest_dot=max(q[2] for q in late),observed_dots=sorted(set(q[2] for q in late)),
   OAM=[248,255,255,255],capture_frame=588,capture_line=192,capture_dot=261,files=meta['files']),
  hardware_signature=dict(context=expected_context,ppu=expected_ppu,error=2),runs=runs,
  diagnosis='Old-bank sprite request at step48 remains in flight across CHR commit; drains at53, new request53, required sample55, response58. Address generation correct; stale physical mapping read consumes deadline. No tile traffic needed.',
  limits=['CPU output bus replay, not CPU instruction execution','external tile/export contention absent; unrelated CPU read included as control','prior 851-second cache/IRQ history not recovered','STOP tested at reader reset boundary; final ACK/menu source unchanged, no new physical execution'],
  protected=dict(independent_sample_deadline=True,STOP_24_cases=True,production_ACK_menu_unchanged=True),
  failed_attempts=failures,selected_sources=inputs)
 (ROOT/'analysis/bonus698-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 archive=dict(stage=698,path=str(a.out/'evidence.zip'),sha256=sha(a.out/'evidence.zip'),files=len(manifest),verified_all=True,private_ROM_and_images_not_in_Git=True)
 (ROOT/'analysis/bonus698-archive.json').write_text(json.dumps(archive,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(pass_=True,cases=24,hardware_identical_faults=12,reference_bank_switches=len(late),archive=archive),ensure_ascii=False))

if __name__=='__main__':main()
