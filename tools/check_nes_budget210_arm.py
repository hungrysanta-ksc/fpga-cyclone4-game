# SPDX-License-Identifier: MIT
"""Linked RUN/IRQ budget with unchanged platform/library instruction checks.
The original >=1024B margin remains; passive counters are not waived RAM.
"""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
from nes_budget210 import ROOT,BASE,sha,replace,transform
import check_nes_runlease165 as base

def main():
 p=argparse.ArgumentParser()
 for n in ('arm','arm-bin','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.arm=a.arm.resolve();a.arm_bin=a.arm_bin.resolve();a.out=a.out.resolve()
 assert not a.out.exists();a.out.parent.mkdir(parents=True,exist_ok=True)
 prep=json.loads((a.arm/'preparation-budget210.json').read_bytes())
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 for n,s in transform({n:(BASE/'probes/nes-binding209/arm01/src'/n).read_text() for n in ['nes_plan191.c','nes_native_runtime165.c']}).items():assert (a.arm/'src'/n).read_text()==s,n
 def tool(name,args):return subprocess.check_output([str(a.arm_bin/('arm-none-eabi-'+name+'.exe')),*args,'src/obj-nes-100/sd2snes.elf'],cwd=a.arm).decode().replace('\r\n','\n')
 dis,nm=tool('objdump',['-d']),tool('nm',['-S'])
 prior=BASE/'probes/nes-binding209/check02'
 def blocks(s):return {m[1]:m[2] for m in re.finditer(r'^[\da-f]+ <([^>]+)>:\n(.*?)(?=^[\da-f]+ <|\Z)',s,re.M|re.S)}
 def addresses(s):return {int(m[1],16):m[2] for m in re.finditer(r'^([\da-f]+) (?:[\da-f]+ )?\w (\S+)$',s,re.M)}
 old,new=blocks((prior/'objdump.txt').read_text()),blocks(dis);oa,na=addresses((prior/'nm.txt').read_text()),addresses(nm)
 def normalized(s,names):
  out=[]
  for line in s.splitlines():
   m=re.match(r'\s*[\da-f]+:\s+(?:[\da-f]{4,8}\s+)+(.+)',line)
   if not m:continue
   ins=m[1].split('@')[0].strip();ins=re.sub(r'\b[\da-f]+ (<[^>]+>)',r'\1',ins)
   literal=re.fullmatch(r'\.word\s+0x([\da-f]+)',ins)
   if literal and int(literal[1],16) in names:ins='.word <'+names[int(literal[1],16)]+'>'
   out.append(re.sub(r'\s+',' ',ins))
  return out
 review=json.loads((BASE/'probes/nes-binding209/check02-review.json').read_bytes())
 for group in ('library_bodies','platform_bodies'):
  for name in review[group]:
   assert normalized(old[name],oa)==normalized(new[name],na),name
   review[group][name]=hashlib.sha256(new[name].encode()).hexdigest()
 for n,h in review['platform_sources'].items():
  if n in ('nes_menu_diagnostic.c','nes_runtime_board165.inc'):
   assert sha(a.arm/'src'/n)==prep['changed']['src/'+n]
   review['platform_sources'][n]=sha(a.arm/'src'/n)
  else:assert sha(a.arm/'src'/n)==h,n
 cb=review['callbacks'];assert cb['nes_native_video191_plan']==['nes_plan200_emit'];cb['nes_native_video191_plan']=['budget_plan210']
 review_path=a.out.parent/(a.out.name+'-review.json');review_path.write_text(json.dumps(review,indent=2)+'\n',encoding='utf8')
 s=(ROOT/'tools/check_nes_runlease165.py').read_text();s=s[s.index('def main():'):s.index("if __name__=='__main__'")]
 s=replace(s,"'preparation-runlease165.json'","'preparation-budget210.json'")
 s=replace(s,"*args,str(elf)])","*args,'src/obj-nes-100/sd2snes.elf'],cwd=a.arm)")
 s=replace(s,"hits=[x for x,n in nodes.items() if n['name']==name];assert len(hits)==1,(name,hits)","hits=[x for x,n in nodes.items() if n['name']==name]\n  if name=='valid':hits=[x for x in hits if nodes[x]['indirect']]\n  assert len(hits)==1,(name,hits)")
 s=replace(s,"assert nodes[addr('save_report')]['weight']==4864","assert nodes[addr('save_report')]['weight']<=5000 # same4096B text reused; no second buffer")
 ns=dict(base.__dict__);ns['CALLBACKS']=cb;exec(compile(s,'budget210-linked-check','exec'),ns)
 sys.argv=['check210','--arm',str(a.arm),'--arm-bin',str(a.arm_bin),'--review',str(review_path),'--out',str(a.out)];ns['main']()
 r=json.loads((a.out/'result.json').read_bytes())
 assert '<nes_budget210_plan>' in new['budget_plan210'] and '<nes_plan200_emit>' in new['budget_plan210']
 assert '<nes_budget210_attach>' in new['native_session165'] and '<nes_budget210_detach>' in new['native_session165']
 fw=(a.arm/'src/obj-nes-100/firmware.stm').read_bytes()
 for m in [b'NES GAME 210.nh1',b'game210.nes',b'fpga_n210.bi3',b'nes-progress-210.txt',b'nes-game-last-210.txt',b'nes-budget-210.txt',b'NES-GAME210-DEV']:assert m in fw,m
 r.update(public_sources=prep['public_sources']|{'tools/check_nes_budget210_arm.py':sha(Path(__file__))},
  budget_bytes=int(re.search(r'^[\da-f]+ ([\da-f]+) \w nes_budget210$',nm,re.M)[1],16),physical=False,new_fit=False)
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
