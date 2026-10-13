# SPDX-License-Identifier: MIT
"""Bound the linked RUN graph and active IRQ stack; not a general C analyzer."""
from pathlib import Path
import argparse,json,re,subprocess,hashlib,struct
from nes_game147 import sha

CALLBACKS={
 'nes_game149_transfer':['load_select','wait_us'],
 'nes_native165_bulk':['load_select','wait_us'],
 'nes_native165_poll':['transfer'],'nes_native165_prepare':['transfer'],
 'guard':['native_ticks165','native_service165'],'transfer':['native_transfer165'],
 'nes_runtime165_begin':['native_ticks165'],'packet':['nes_sink_spi165_exchange'],
 'nes_native_video165_build':['nes_sink165_pattern'],
 'nes_sink_spi165_exchange':['guard','transfer'],'internal_nprintf':['outchar','outstr'],
}
# Reviewed ARM prologues. Leaf library bodies must match the pinned instruction
# fingerprints in the review JSON; a different compiler requires a new review.
EXTRA={'__aeabi_uldivmod':16,'__aeabi_idiv0':0,'memcpy':0,'strlen':8,
 'crc8.constprop.0':12,'__udivmoddi4':32,'memcmp':0,'memset':0}
def main():
 p=argparse.ArgumentParser()
 for n in ['arm','arm-bin','review','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);obj=a.arm/'src/obj-nes-100';elf=obj/'sd2snes.elf';fw=obj/'firmware.stm'
 prep=json.loads((a.arm/'preparation-runlease165.json').read_bytes())
 for n,h in prep['copied'].items():assert sha(a.arm/n)==prep['changed'].get(n,h),n
 for n,h in prep['added'].items():assert sha(a.arm/n)==h,n
 def tool(n,args):
  data=subprocess.check_output([str(a.arm_bin/('arm-none-eabi-'+n+'.exe')),*args,str(elf)]);(a.out/(n+'.txt')).write_bytes(data)
  return data.decode().replace('\r\n','\n')
 dis=tool('objdump',['-d']);symbols=tool('nm',['-S']);tool('size',['-A'])
 su={};supins={}
 for f in obj.rglob('*.su'):
  supins[f.relative_to(obj).as_posix()]=sha(f)
  for line in f.read_text().splitlines():
   loc,n,kind=line.split('\t');name=loc.rsplit(':',1)[-1];su.setdefault(name,[]).append((int(n),kind))
 blocks={int(m[1],16):(m[2],m[3]) for m in re.finditer(r'^([\da-f]+) <([^>]+)>:\n(.*?)(?=^[\da-f]+ <|\Z)',dis,re.M|re.S)}
 nodes={}
 for address,(name,body) in blocks.items():
  weights=su.get(name,[]);edges=set();indirect=[];selfcall=False
  for line in body.splitlines():
   m=re.search(r'\b(?:bl|blx|b|bne|beq|bhi|bls|bcc|bcs|bgt|blt|bge|ble|bpl|bmi|bvs|bvc)(?:\.[nw])?\s+([\da-f]+) <([^>]+)>',line)
   if not m:m=re.search(r'\bcbn?z\s+\w+,\s*([\da-f]+) <([^>]+)>',line)
   if m:
    to=int(m[1],16)
    if to==address and re.search(r'\bblx?\b',line):selfcall=True
    elif to in blocks and to!=address:edges.add(to)
   if re.search(r'\bblx\s+(?:r\d+|ip|lr|sl|fp|sb)|\bbx\s+(?:r(?:[0-9]|1[0-2])|ip|sl|fp|sb)\b',line):indirect.append(line.strip())
  nodes[address]=dict(name=name,weight=max((x[0] for x in weights),default=None),usage=weights,edges=sorted(edges),indirect=indirect,selfcall=selfcall,body=body)
 def addr(name):
  hits=[x for x,n in nodes.items() if n['name']==name];assert len(hits)==1,(name,hits);return hits[0]
 transfers=[x for x,n in nodes.items() if n['name']=='transfer' and addr('guard') in n['edges']];assert len(transfers)==1
 def resolve(name):return transfers[0] if name=='transfer' else addr(name)
 for name,targets in CALLBACKS.items():
  node=nodes[resolve(name)];assert node['indirect'];node['edges']=sorted(set(node['edges']+[resolve(t) for t in targets]))
 seen=set()
 def visit(x):
  if x in seen:return
  seen.add(x)
  for y in nodes[x]['edges']:visit(y)
 roots=['native_session165','SysTick_Handler','TIM2_IRQHandler','NMI_Handler']
 for name in roots:visit(addr(name))
 review=json.loads(a.review.read_bytes());assert review['callbacks']==CALLBACKS
 for x in seen:
  n=nodes[x];assert all(k=='static' for _,k in n['usage']),n['name']
  assert not n['indirect'] or n['name'] in CALLBACKS,n['name']
  assert not n['selfcall'] or n['name']=='uart_putc',n['name']
  if n['weight'] is None:
   n['weight']=EXTRA[n['name']]
   assert hashlib.sha256(n['body'].encode()).hexdigest()==review['library_bodies'][n['name']],n['name']
 def maximum(x,trail=()):
  assert x not in trail,trail
  n=nodes[x];best=max([maximum(y,trail+(x,)) for y in n['edges']],default=(0,[]))
  own=n['weight']*(2 if n['selfcall'] else 1)
  return own+best[0],[(n['name'],own)]+best[1]
 paths={name:maximum(addr(name)) for name in roots}
 callers=['main','nes_menu_diagnostic_run','nes_menu_sd_probe']
 for left,right in zip(callers,callers[1:]+['native_session165']):assert addr(right) in nodes[addr(left)]['edges'],(left,right)
 foreground=sum(nodes[addr(n)]['weight'] for n in callers)+paths['native_session165'][0]
 # Reserve FP-extended frame104B + alignment4B at EACH of SysTick/TIM2/NMI.
 # Actual normal code has no FP use; this deliberately allows the larger frame.
 irq=sum(paths[n][0]+108 for n in roots[1:])
 heap=int(re.search(r'^([\da-f]+) \w __heap_start$',symbols,re.M)[1],16)
 top=int(re.search(r'^([\da-f]+) \w __stack$',symbols,re.M)[1],16);assert top==0x20010000
 free=top-heap;assert free-foreground-irq>=1024,(free,foreground,irq)
 assert not re.search(r'\b(?:_malloc_r|malloc|_sbrk|sbrk)\b',symbols)
 assert not any(n in symbols for n in ['native_receiver165','native_work165','nes_runtime165_log_buffer'])
 # Fail-stop is retained; it cannot recurse or allocate after a clock fault.
 stop=nodes[addr('stop108')]['body'];assert 'cpsid' in stop and not re.search(r'\bblx?\b',stop)
 assert len(re.findall(r'\bstr(?:\.w)?\s',stop))==15
 assert struct.unpack_from('<I',fw.read_bytes(),0x208)[0]==(addr('NMI_Handler')|1)
 src=a.arm/'src';run=(src/'nes_run136.inc').read_text();adapter=(src/'nes_runtime_board165.inc').read_text()
 assert 'rx[1]!=0xe6||rx[7]!=2' in run and 'candidate->board_id=0x74' in run
 assert 'native_runtime165.receiver=NULL;native_runtime165.video=NULL;native_io165=NULL;' in adapter
 assert nodes[addr('save_report')]['weight']==4864
 assert addr('save_report') not in seen
 assert 'native_runtime165.receiver->' not in (src/'nes_menu_diagnostic.c').read_text()
 for n,h in review['platform_sources'].items():assert sha(src/n)==h,n
 for n in ['SysTick_Hook','TIM2_IRQHandler','NMI_Handler','stop108','uart_putc']:
  assert hashlib.sha256(nodes[addr(n)]['body'].encode()).hexdigest()==review['platform_bodies'][n],n
 # Compiler follows literal SP stack release on native_session return; pointer
 # revocation, noinline and absence of malloc are required lifetime premises.
 result=dict(passed=True,firmware_sha256=sha(fw),firmware_bytes=fw.stat().st_size,elf_sha256=sha(elf),ram_static=heap-0x20000070,ram_free_outside_run=free,foreground_bound=foreground,irq_reserve=irq,remaining_margin=free-foreground-irq,paths=paths,callers=[(n,nodes[addr(n)]['weight']) for n in callers],reachable=len(seen),stack_files=supins,review_sha256=sha(a.review),public_sources={n:sha(Path(__file__).parent.parent/n) for n in ['tools/check_nes_runlease165.py','tools/nes_runlease165.py','src/nes/firmware/nes_runlease165.inc']},hardware_package=False,physical=False,scope='Conservative linked RUN graph including callbacks and fault helpers; reviewed enabled SysTick/TIM2/NMI plus extended hardware frames. No exhaustive proof of unchanged menu/GBC call graphs; their permanent33952B allocation is removed. Not measured high-water or real hardware.')
 (a.out/'reachable.json').write_text(json.dumps({hex(x):{k:v for k,v in nodes[x].items() if k!='body'} for x in sorted(seen)},indent=2)+'\n')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['paths','stack_files','public_sources']}))
if __name__=='__main__':main()
