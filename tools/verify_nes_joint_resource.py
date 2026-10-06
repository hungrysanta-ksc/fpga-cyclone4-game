# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,re,collections
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def number(pattern,text):
 m=re.search(pattern,text);assert m,pattern;return int(m[1].replace(',',''))
def inspect(run,repo):
 m=json.loads((run/'result.json').read_text())
 assert m['phases']=={'map':0,'fit':0} and not m['hardware_eligible']
 assert m['driver_sha256']==sha(repo/'tools/nes_joint_resource.py')
 for name,digest in m['sources'].items():assert sha(run/name)==digest,name
 old=repo/'analysis/local-resource-018/ram-01';cm=json.loads((old/'result.json').read_text())
 assert m['core_reference_sha256']==sha(old/'result.json')
 for name,digest in cm['sources'].items():assert sha(run/name)==sha(old/name)==digest
 tm=json.loads((repo/'analysis/local-snes-frontend-031/resource/result.json').read_text())
 assert m['transport_reference_sha256']==sha(repo/'analysis/local-snes-frontend-031/resource/result.json')
 for name,digest in tm['sources'].items():assert sha(run/name)==sha(repo/'src/nes'/name)==digest
 fit=(run/'output_files/joint.fit.summary').read_text(encoding='latin-1')
 rpt=(run/'output_files/joint.fit.rpt').read_text(encoding='latin-1')
 assert 'Fitter Status : Successful' in fit and 'EP4CE15F17C8' in fit
 metrics={'LE':number(r'Total logic elements\s*:\s*([\d,]+)',fit),'registers':number(r'Total registers\s*:\s*([\d,]+)',fit),
  'LAB':number(r'Total LABs:\s*partially or completely used\s*;\s*([\d,]+)',rpt),'M9K':number(r'; M9Ks\s*;\s*([\d,]+)',rpt),
  'memory_bits':number(r'Total memory bits\s*:\s*([\d,]+)',fit),'virtual_pins':number(r'Total virtual pins\s*:\s*([\d,]+)',fit),
  'physical_pins':number(r'Total pins\s*:\s*([\d,]+)',fit)}
 assert metrics['memory_bits']==172032 and metrics['M9K']==24 and metrics['virtual_pins']==281 and metrics['physical_pins']==2
 entities={}
 wanted=['nes_resource:nes','nes_transport:transport','T65:cpu','PPU:ppu','OAMEval:spriteeval','APU:apu','MMC3:mapper','nes_resource_ram:cpu_ram','nes_resource_ram:prg_ram','nes_resource_ram:ciram','nes_packet_queue_ram:queue','nes_host_stage:stage','nes_snes_frontend:frontend']
 for line in rpt.splitlines():
  fields=[s.strip() for s in line.split(';')][1:-1]
  if len(fields)>6:
   name=fields[0].strip('|')
   if name in wanted and re.match(r'^\d+',fields[1]):
    entities[name]={'logic_cells':int(fields[1].split()[0]),'registers':int(fields[2].split()[0]),'memory_bits':int(fields[4]),'M9K':int(fields[5])}
 for name in wanted:assert name in entities,name
 for name in ['T65:cpu','PPU:ppu','APU:apu','MMC3:mapper','nes_snes_frontend:frontend']:assert entities[name]['logic_cells']>0
 for name,bits,blocks in [('nes_resource_ram:cpu_ram',16384,2),('nes_resource_ram:ciram',16384,2),('nes_resource_ram:prg_ram',65536,8),('nes_packet_queue_ram:queue',49152,8),('nes_host_stage:stage',24576,4)]:
  assert entities[name]['memory_bits']==bits and entities[name]['M9K']==blocks,(name,entities[name])
 warnings={}
 for phase in ('map','fit'):
  log=(run/(phase+'.log')).read_text(encoding='latin-1')
  assert not re.search(r'(?m)^\s*Error \(\d+\)',log)
  warnings[phase]=dict(collections.Counter(re.findall(r'(?m)^\s*(?:Critical )?Warning \((\d+)\)',log)))
 return {'candidate':m['candidate'],'area_fit_passed':True,'hardware_eligible':False,'seed':m['seed'],'resources':metrics,'entities':entities,
 'headroom':{'LE':15408-metrics['LE'],'LAB':963-metrics['LAB'],'M9K':56-metrics['M9K'],'LE_to_internal13000':13000-metrics['LE']},
 'separate_sum':{'LE':13420,'LAB':992,'M9K':24},'warning_codes':warnings,'core_and_transport_source_bytes_unchanged':True,
 'limits':'Co-placement only; packet producer inputs remain external. No live video integration,boardPLL/loader/memoryservice/physicalIO/STA or functional validation of018 RAM adapter.',
 'verifier_sha256':sha(__file__)}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 result=inspect(a.run,Path(__file__).resolve().parents[1]);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
