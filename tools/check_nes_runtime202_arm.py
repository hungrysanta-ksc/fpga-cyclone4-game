# SPDX-License-Identifier: MIT
"""Recompute the complete RUN/IRQ graph, including nested direct-plan callbacks.
Keep the established >=1024-byte margin gate; report a failure, never waive it.
"""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
from nes_runtime202 import ROOT,BASE,sha
from nes_clip178 import replace
import check_nes_runlease165 as base

def main():
 p=argparse.ArgumentParser()
 for n in ('arm','arm-bin','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.arm=a.arm.resolve();a.arm_bin=a.arm_bin.resolve();a.out=a.out.resolve()
 assert not a.out.exists();a.out.parent.mkdir(parents=True,exist_ok=True)
 prior=BASE/'probes/nes-paired186/check01'
 def tool(name,args):return subprocess.check_output([str(a.arm_bin/('arm-none-eabi-'+name+'.exe')),*args,'src/obj-nes-100/sd2snes.elf'],cwd=a.arm).decode().replace('\r\n','\n')
 dis=tool('objdump',['-d']);nm=tool('nm',['-S'])
 def blocks(s):return {m[1]:m[2] for m in re.finditer(r'^[\da-f]+ <([^>]+)>:\n(.*?)(?=^[\da-f]+ <|\Z)',s,re.M|re.S)}
 def addresses(s):return {int(m[1],16):m[2] for m in re.finditer(r'^([\da-f]+) (?:[\da-f]+ )?\w (\S+)$',s,re.M)}
 old,new=blocks((prior/'objdump.txt').read_text()),blocks(dis)
 oa,na=addresses((prior/'nm.txt').read_text()),addresses(nm)
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
 review=json.loads((BASE/'probes/nes-paired186/armreview01.json').read_bytes())
 for group in ('library_bodies','platform_bodies'):
  for name in review[group]:
   assert normalized(old[name],oa)==normalized(new[name],na),name
   review[group][name]=hashlib.sha256(new[name].encode()).hexdigest()
 for n,h in review['platform_sources'].items():assert sha(a.arm/'src'/n)==h,n
 cb=review['callbacks'];del cb['nes_native_video185_build']
 cb.update(nes_native_video191_plan=['nes_plan200_emit'],valid=['guard'],poll=['guard','transfer'],flush=['guard','transfer'],nes_plan200_retire=['guard','transfer'])
 review_path=a.out.parent/(a.out.name+'-review.json');review_path.write_text(json.dumps(review,indent=2)+'\n',encoding='utf8')
 source=(ROOT/'tools/check_nes_runlease165.py').read_text();source=source[source.index('def main():'):source.index("if __name__=='__main__'")]
 source=replace(source,"'preparation-runlease165.json'","'preparation-runtime202.json'")
 source=replace(source,"*args,str(elf)])","*args,'src/obj-nes-100/sd2snes.elf'],cwd=a.arm)")
 source=replace(source,"hits=[x for x,n in nodes.items() if n['name']==name];assert len(hits)==1,(name,hits)",
 "hits=[x for x,n in nodes.items() if n['name']==name]\n  if name=='valid':hits=[x for x in hits if nodes[x]['indirect']] # window's pure valid has no callback\n  assert len(hits)==1,(name,hits)")
 source=replace(source,"free=top-heap;assert free-foreground-irq>=1024,(free,foreground,irq)","free=top-heap;memory_ok=free-foreground-irq>=1024")
 source=replace(source,'result=dict(passed=True,','result=dict(passed=memory_ok,')
 source=replace(source,"(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\\n');print", "result.update(runtime202=True,minimum_margin=1024,old_chr_ingress_retained=True,actual_scroll_measured=False)\n (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\\n');print")
 source+='\n assert memory_ok,(free,foreground,irq,free-foreground-irq)\n'
 ns=dict(base.__dict__);ns['CALLBACKS']=cb;exec(compile(source,'runtime202-linked-check','exec'),ns)
 sys.argv=['check202','--arm',str(a.arm),'--arm-bin',str(a.arm_bin),'--review',str(review_path),'--out',str(a.out)]
 ns['main']()
 assert '<nes_native_video191_plan>' in new['nes_runtime165_step'] and '<nes_plan200_finish>' in new['nes_runtime165_step']
 assert '<nes_plan200_retire>' in new['nes_runtime165_step'] and '<nes_sink165_pattern>' not in new['nes_runtime165_step']
 assert b'NES-RUN202-DEV' in (a.arm/'src/obj-nes-100/firmware.stm').read_bytes()
 r=json.loads((a.out/'result.json').read_bytes());r['public_sources'].update({n:sha(ROOT/n) for n in ('tools/check_nes_runtime202_arm.py','tools/nes_runtime202_arm.py','tools/nes_runtime202.py','src/nes/firmware/nes_runtime202.c','src/nes/firmware/nes_runtime202.h')})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
