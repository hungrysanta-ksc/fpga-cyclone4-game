# SPDX-License-Identifier: MIT
"""Linked maintained-slot RUN + IRQ bound; unchanged platform instruction proof."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
from nes_runtime213 import ROOT,BASE,sha,once,runtime
import check_nes_runlease165 as base

def main():
 p=argparse.ArgumentParser()
 for n in ('arm','arm-bin','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.arm=a.arm.resolve();a.arm_bin=a.arm_bin.resolve();a.out=a.out.resolve()
 assert not a.out.exists();a.out.parent.mkdir(parents=True,exist_ok=True)
 prep=json.loads((a.arm/'preparation-runtime213.json').read_bytes())
 for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
 assert (a.arm/'src/nes_native_runtime165.c').read_text()==runtime((BASE/'probes/nes-budget210/arm03/src/nes_native_runtime165.c').read_text())
 def tool(name,args):return subprocess.check_output([str(a.arm_bin/('arm-none-eabi-'+name+'.exe')),*args,'src/obj-nes-100/sd2snes.elf'],cwd=a.arm).decode().replace('\r\n','\n')
 dis,nm=tool('objdump',['-d']),tool('nm',['-S'])
 prior=BASE/'probes/nes-budget210/check02'
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
 review=json.loads((BASE/'probes/nes-budget210/check02-review.json').read_bytes())
 for group in ('library_bodies','platform_bodies'):
  for name in review[group]:
   assert normalized(old[name],oa)==normalized(new[name],na),name
   review[group][name]=hashlib.sha256(new[name].encode()).hexdigest()
 for n,h in review['platform_sources'].items():
  if n in ('nes_menu_diagnostic.c','nes_runtime_board165.inc','nes_run136.inc'):
   assert sha(a.arm/'src'/n)==prep['changed']['src/'+n]
   review['platform_sources'][n]=sha(a.arm/'src'/n)
  else:assert sha(a.arm/'src'/n)==h,n
 cb=review['callbacks'];assert cb.pop('nes_native_video191_plan')==['budget_plan210']
 cb['nes_resident211_slot']=['resident_plan213']
 review_path=a.out.parent/(a.out.name+'-review.json');review_path.write_text(json.dumps(review,indent=2)+'\n',encoding='utf8')
 s=(ROOT/'tools/check_nes_runlease165.py').read_text();s=s[s.index('def main():'):s.index("if __name__=='__main__'")]
 s=once(s,"'preparation-runlease165.json'","'preparation-runtime213.json'")
 s=once(s,"*args,str(elf)])","*args,'src/obj-nes-100/sd2snes.elf'],cwd=a.arm)")
 s=once(s,"hits=[x for x,n in nodes.items() if n['name']==name];assert len(hits)==1,(name,hits)","hits=[x for x,n in nodes.items() if n['name']==name]\n  if name=='valid':hits=[x for x in hits if nodes[x]['indirect']]\n  assert len(hits)==1,(name,hits)")
 s=once(s,"assert nodes[addr('save_report')]['weight']==4864","assert nodes[addr('save_report')]['weight']<=5000")
 ns=dict(base.__dict__);ns['CALLBACKS']=cb;exec(compile(s,'runtime213-linked-check','exec'),ns)
 sys.argv=['check213','--arm',str(a.arm),'--arm-bin',str(a.arm_bin),'--review',str(review_path),'--out',str(a.out)];ns['main']()
 r=json.loads((a.out/'result.json').read_bytes())
 assert '<nes_plan200_emit>' in new['resident_plan213']
 assert '<nes_budget210_attach>' not in new['native_session165']
 assert '<nes_resident211_reset>' in new['nes_runtime165_begin']
 assert 'native_runtime165.resident=NULL;' in (a.arm/'src/nes_runtime_board165.inc').read_text()
 fw=(a.arm/'src/obj-nes-100/firmware.stm').read_bytes()
 for m in [b'NES GAME 213.nh1',b'game213.nes',b'fpga_n213.bi3',b'nes-progress-213.txt',b'nes-game-last-213.txt',b'nes-budget-213.txt',b'NES-GAME213-DEV']:assert m in fw,m
 r.update(public_sources=prep['public_sources']|{'tools/check_nes_runtime213_arm.py':sha(Path(__file__))},physical=False,new_fit=False,hardware_package=False)
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
