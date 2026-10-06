# Parse raw Quartus resource/STA evidence; no board signoff. SPDX-License-Identifier: MIT.
from pathlib import Path
import argparse,json,re,hashlib,collections
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def raw(p):return p.read_bytes().decode('latin1') # ASCII report fields; retain original locale bytes on disk.
def number(pattern,text):
 m=re.search(pattern,text);assert m,pattern
 return int(m[1].replace(',',''))
def inspect(p):
 result=json.loads((p/'result.json').read_text());assert result['phases']==dict(map=0,fit=0,sta=0) and not result['hardware_eligible']
 for f,h in result['sources'].items():assert sha(p/f)==h,f
 fit=raw(p/'output_files/probe.fit.summary');report=raw(p/'output_files/probe.fit.rpt');sta=raw(p/'output_files/probe.sta.rpt');summary=raw(p/'output_files/probe.sta.summary')
 assert 'Fitter Status : Successful' in fit and 'EP4CE15F17C8' in fit
 metrics=dict(logic_elements=number(r'Total logic elements\s*:\s*([\d,]+)',fit),registers=number(r'Total registers\s*:\s*([\d,]+)',fit),memory_bits=number(r'Total memory bits\s*:\s*([\d,]+)',fit),virtual_pins=number(r'Total virtual pins\s*:\s*([\d,]+)',fit),labs=number(r'Total LABs:\s*partially or completely used\s*;\s*([\d,]+)',report),m9k=number(r'; M9Ks\s*;\s*([\d,]+)',report),plls=number(r'Total PLLs\s*:\s*([\d,]+)',fit))
 timing=re.findall(r'Type\s*:\s*(.*?)\r?\nSlack\s*:\s*([\d.-]+)\r?\nTNS\s*:\s*([\d.-]+)',summary)
 assert len(timing)==15 and all(float(s)>=0 and float(t)==0 for _,s,t in timing)
 minimum={c:min(float(s) for t,s,_ in timing if c in t) for c in ('Setup','Hold','Recovery','Removal','Minimum Pulse Width')}
 unconstrained={}
 for label in ('Illegal Clocks','Unconstrained Clocks','Unconstrained Input Ports','Unconstrained Output Ports','Unconstrained Input Port Paths','Unconstrained Output Port Paths'):
  m=re.search(r'; '+label+r'\s*;\s*(\d+)\s*;\s*(\d+)',sta);assert m,label;unconstrained[label]=dict(setup=int(m[1]),hold=int(m[2]))
 assert unconstrained['Unconstrained Clocks']['setup']==0 and unconstrained['Unconstrained Input Ports']['setup']>0
 entities={}
 for line in report.splitlines():
  fields=[s.strip() for s in line.split(';')][1:-1]
  if len(fields)>6 and re.fullmatch(r'\|(?:APU:apu|PPU:ppu|OAMEval:spriteeval|T65:cpu|MMC3:mapper|nes_resource_ram:(?:cpu_ram|ciram|prg_ram))\|',fields[0]):
   entities[fields[0]]=dict(logic_cells=int(fields[1].split()[0]),registers=int(fields[2].split()[0]),memory_bits=int(fields[4]),m9k=int(fields[5]))
 for name in ('|T65:cpu|','|PPU:ppu|','|APU:apu|','|MMC3:mapper|'):assert entities[name]['logic_cells']>0
 if result['local_ram']:
  assert metrics['m9k']==12 and metrics['memory_bits']==98304
  for name,bits,blocks in [('cpu_ram',16384,2),('ciram',16384,2),('prg_ram',65536,8)]:
   e=entities['|nes_resource_ram:'+name+'|'];assert e['memory_bits']==bits and e['m9k']==blocks
 else:assert metrics['m9k']==0 and metrics['memory_bits']==0
 warnings={}
 for phase in ('map','fit','sta'):
  log=raw(p/(phase+'.log'));assert not re.search(r'(?m)^\s*Error \(\d+\)',log)
  warnings[phase]=dict(collections.Counter(re.findall(r'(?m)^\s*(?:Critical )?Warning \((\d+)\)',log)))
 return dict(local_ram=result['local_ram'],resources=metrics,min_slack_ns=minimum,unconstrained=unconstrained,entities=entities,warning_codes=warnings,raw_report_hashes={f:sha(p/f) for f in ['result.json','probe.qsf','probe.sdc','map.log','fit.log','sta.log','output_files/probe.fit.summary','output_files/probe.fit.rpt','output_files/probe.sta.summary','output_files/probe.sta.rpt']})
def main():
 p=argparse.ArgumentParser()
 for n in ('logic','ram','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();logic=inspect(a.logic);ram=inspect(a.ram);r=ram['resources']
 result=dict(candidate='NES-R1-RESOURCE-018',resource_fit_passed=True,hardware_eligible=False,functional_validation_of_new_adapter_and_ram=False,logic=logic,ram=ram,arithmetic_headroom=dict(le_hard_limit=15408-r['logic_elements'],le_to_design_target13000=13000-r['logic_elements'],unused_labs=963-r['labs'],unused_m9k=56-r['m9k']),scope='Two virtual-pin resource probes, same46.560846ns master/seed1. Internal constrained timing only; unconstrained external IO and unassigned clock pin remain. No full board timing, memory arbitration, display transport or game functionality signoff.',verifier_sha256=sha(Path(__file__)))
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(resource_fit_passed=True,logic=logic['resources'],ram=ram['resources'],headroom=result['arithmetic_headroom'],ram_min_slack_ns=ram['min_slack_ns'],hardware_eligible=False),indent=2))
if __name__=='__main__':main()