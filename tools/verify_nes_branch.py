"""Check original branch bus cycles against an address oracle and Mesen. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,hashlib,json,re,copy

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rtl_rows(p):
 return [dict(zip(('tick','address','read','data','case','last'),map(int,s.split()))) for s in p.read_text().splitlines()]
def mesen_rows(p):
 rows=[]
 for s in p.read_text().splitlines():
  k,*v=s.split();rows.append(dict(kind=k,**dict(zip(('cycle','address','data','case'),map(int,v)))))
 return rows

def compare(cases,prg,rtl,mesen):
 errors=[];results=[]
 def error(n,msg):errors.append(dict(case=n,reason=msg))
 for c in cases:
  n=c['id'];b=c['branch'];op=prg[b-0x8000];operand=prg[b+1-0x8000];offset=operand if operand<128 else operand-256
  masks={0x90:1,0xb0:1,0xf0:2,0xd0:2,0x30:128,0x10:128,0x50:64,0x70:64}
  positive=op in (0xb0,0xf0,0x30,0x70);taken=bool(c['flags']&masks[op])==positive
  target=(b+2+offset)&65535;cross=(b+2)&0xff00!=target&0xff00
  dummy=([b+2]+([((b+2)&0xff00)|(target&255)] if cross else [])) if taken else []
  addresses=[b,b+1]+dummy;cycles=len(addresses);nextpc=target if taken else b+2
  assert (target,taken,dummy,cycles,nextpc)==(c['target'],c['taken'],c['dummy_reads'],c['cycles'],c['next_pc'])
  starts=[i for i,r in enumerate(rtl) if r['case']==n and r['address']==b and r['read'] and r['data']==op]
  if len(starts)!=1:error(n,'rtl_branch_occurrence');continue
  i=starts[0];bus=rtl[i:i+cycles];after=rtl[i+cycles:i+cycles+1]
  actual=[r['address'] for r in bus]
  if actual!=addresses:error(n,'rtl_bus_address')
  if len(bus)!=cycles or not after or after[0]['address']!=nextpc:error(n,'rtl_next_opcode')
  if any(r['read']!=1 or r['data']!=prg[r['address']-0x8000] for r in bus):error(n,'rtl_bus_value_or_direction')
  if len(bus)==cycles and after and [r['tick']-bus[0]['tick'] for r in bus+after]!=list(range(0,(cycles+1)*12,12)):error(n,'rtl_cycle_spacing')
  starts=[i for i,r in enumerate(mesen) if r['case']==n and r['kind']=='X' and r['address']==b]
  if len(starts)!=1:error(n,'mesen_branch_occurrence');continue
  j=starts[0];end=next((k for k in range(j+1,len(mesen)) if mesen[k]['kind']=='X'),None)
  if end is None:error(n,'mesen_incomplete');continue
  mr=mesen[j+1:end];mx=mesen[end];m0=mesen[j]
  if [(r['kind'],r['address'],r['cycle']-m0['cycle']) for r in mr]!=[('R',a,k+3) for k,a in enumerate(dummy)]:error(n,'mesen_dummy_reads')
  if any(r['data']!=prg[r['address']-0x8000] for r in mr):error(n,'mesen_dummy_data')
  if mx['address']!=nextpc or mx['cycle']-m0['cycle']!=cycles:error(n,'mesen_next_opcode_or_cycles')
  results.append(dict(id=n,name=c['name'],mode=c['mode'],cycles=cycles,expected_bus_addresses=addresses,rtl_bus_addresses=actual,mesen_dummy_addresses=[r['address'] for r in mr],next_pc=nextpc))
 return dict(passed=not errors,errors=errors,cases=results)

def main():
 p=argparse.ArgumentParser()
 for n in ('rom','rtl','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();manifest=json.loads((a.rom/'manifest.json').read_text());rom=(a.rom/'branch.nes').read_bytes();assert sha(a.rom/'branch.nes')==manifest['sha256'];prg=rom[16:16+32768]
 rtl=rtl_rows(a.rtl/'branch-bus.tsv');mesen=mesen_rows(a.mesen/'branch-bus.tsv');result=compare(manifest['cases'],prg,rtl,mesen)
 log=(a.rtl/'simulation.log').read_text();build=json.loads((a.rtl/'build.json').read_text());capture=json.loads((a.mesen/'capture.json').read_text())
 assert 'PASS NES DIAGNOSTIC' in log and not re.search(r'\*\* (?:Fatal|Error):',log) and build['diagnostic_passed'] and capture['exit_code']==0
 assert all(sha(a.rom/n)==sha(a.rtl/n) for n in ['prg.hex','manifest.json'])
 negative={};case=manifest['cases'][1];idx=next(i for i,r in enumerate(rtl) if r['case']==case['id'] and r['address']==case['branch'])
 for kind in ['address','tick','read','data','truncate']:
  mutant=copy.deepcopy(rtl)
  if kind=='truncate':mutant=mutant[:idx+2]
  elif kind=='tick':mutant[idx+2][kind]+=12
  elif kind=='read':mutant[idx+2][kind]=0
  else:mutant[idx+2][kind]^=1
  negative[kind]=not compare(manifest['cases'],prg,mutant,mesen)['passed']
 result.update(candidate='NES-P2-BRANCH-011',rom_sha256=sha(a.rom/'branch.nes'),rtl_trace_sha256=sha(a.rtl/'branch-bus.tsv'),mesen_trace_sha256=sha(a.mesen/'branch-bus.tsv'),verifier_sha256=sha(Path(__file__)),negative_tests=negative,scope='56 original branch cases, ideal memory, interrupts disabled. Mesen exec callbacks delimit instructions; read callbacks observe discarded reads only. Not full CPU/IRQ/PPU/APU/hardware conformance.')
 result['passed']=result['passed'] and all(negative.values())
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=result['passed'],cases=len(result['cases']),errors=result['errors'],negative_tests=negative),indent=2));raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
