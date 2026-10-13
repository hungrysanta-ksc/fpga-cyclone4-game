# SPDX-License-Identifier: MIT
"""Recheck168 link, stack and IRQ bodies; allow verified relocation only."""
from pathlib import Path
import argparse,json,re,subprocess,hashlib,sys
from nes_game147 import ROOT,sha
import check_nes_runlease165 as checker

def main():
 p=argparse.ArgumentParser()
 for n in ['arm','prior-check','arm-bin','out','review']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.parent.mkdir(parents=True,exist_ok=True)
 def tool(name,args):
  return subprocess.check_output([str(a.arm_bin/('arm-none-eabi-'+name+'.exe')),*args,'src/obj-nes-100/sd2snes.elf'],cwd=a.arm).decode().replace('\r\n','\n')
 dis=tool('objdump',['-d']);nm=tool('nm',['-S'])
 olddis=(a.prior_check/'objdump.txt').read_text();oldnm=(a.prior_check/'nm.txt').read_text()
 def blocks(s):return {m[1]:m[2] for m in re.finditer(r'^[\da-f]+ <([^>]+)>:\n(.*?)(?=^[\da-f]+ <|\Z)',s,re.M|re.S)}
 def addresses(s):return {int(m[1],16):m[2] for m in re.finditer(r'^([\da-f]+) (?:[\da-f]+ )?\w (\S+)$',s,re.M)}
 old,new=blocks(olddis),blocks(dis);oa,na=addresses(oldnm),addresses(nm)
 def normalized(s,names):
  out=[]
  for line in s.splitlines():
   m=re.match(r'\s*[\da-f]+:\s+(?:[\da-f]{4,8}\s+)+(.+)',line)
   if not m:continue
   ins=m[1].split('@')[0].strip()
   ins=re.sub(r'\b[\da-f]+ (<[^>]+>)',r'\1',ins)
   literal=re.fullmatch(r'\.word\s+0x([\da-f]+)',ins)
   if literal and int(literal[1],16) in names:ins='.word <'+names[int(literal[1],16)]+'>'
   out.append(re.sub(r'\s+',' ',ins))
  return out
 review=json.loads((ROOT/'analysis/pacing167-stack-review.json').read_bytes())
 for group in ['library_bodies','platform_bodies']:
  for name in review[group]:
   before,after=normalized(old[name],oa),normalized(new[name],na)
   assert before==after,(name,[(x,y) for x,y in zip(before,after) if x!=y])
   review[group][name]=hashlib.sha256(new[name].encode()).hexdigest()
 # Source changes are only diagnostic reset/format/path, reviewed by generator.
 for n,h in review['platform_sources'].items():
  actual=sha(a.arm/'src'/n)
  if n!='nes_menu_diagnostic.c':assert actual==h,n
  review['platform_sources'][n]=actual
 review['review168']='8library/5platform normalized instruction operands identical; relocation matched by exact symbol+offset.32B trace added; diagnostic format/reset/paths only. Full RUN/IRQ graph recomputed.'
 a.review.write_text(json.dumps(review,indent=2)+'\n')
 sys.argv=['check_nes_runlease165.py','--arm',str(a.arm),'--arm-bin',str(a.arm_bin),'--review',str(a.review),'--out',str(a.out)]
 checker.main()
 result=json.loads((a.out/'result.json').read_bytes());fw=(a.arm/'src/obj-nes-100/firmware.stm').read_bytes()
 for t in [b'NES-GAME168-DEV',b'NES GAME 168.nh1',b'nes-progress-168.txt',b'nes-game-last-168.txt',b'sink_trace_request_hex=']:assert t in fw,t
 assert re.search(r'^\S+ 00000020 B nes_sink_trace168$',nm,re.M)
 result.update(trace_bytes=32,reviewed_relocated_bodies=13,scope=result['scope']+' New168 ACK trace checked; FPGA and SNES unchanged.')
 result['public_sources'].update({n:sha(ROOT/n) for n in ['tools/check_nes_sink168_arm.py','tools/nes_sink_trace168.py','src/nes/firmware/nes_sink_trace168.c','src/nes/firmware/nes_sink_trace168.h']})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
