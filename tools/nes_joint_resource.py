# SPDX-License-Identifier: MIT
# Co-placement resource probe, not a functional NES-to-SNES integration.
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ports(source,module):
 header=source.split('module '+module+'(',1)[1].split(');',1)[0]
 result=[];direction=None;width=''
 for raw in header.split(','):
  item=raw.strip()
  match=re.fullmatch(r'(input|output)\s+wire\s*(\[[^\]]+\])?\s*(\w+)',item)
  if match:direction,width,name=match.groups();width=width or ''
  else:
   assert direction and re.fullmatch(r'\w+',item),item
   name=item
  result.append((direction,width,name))
 return result
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--out',type=Path,required=True);p.add_argument('--quartus-bin',type=Path,required=True)
 p.add_argument('--seed',type=int,default=1)
 a=p.parse_args();repo=Path(__file__).resolve().parents[1];out=a.out.resolve()
 assert str(out).isascii() and not out.exists()
 core=repo/'analysis/local-resource-018/ram-01';cm=json.loads((core/'result.json').read_text())
 assert cm['local_ram'] and cm['phases']=={'map':0,'fit':0,'sta':0}
 for name,digest in cm['sources'].items():assert sha(core/name)==digest,name
 tm=json.loads((repo/'analysis/local-snes-frontend-031/resource/result.json').read_text())
 assert tm['phases']=={'map':0,'fit':0}
 for name,digest in tm['sources'].items():assert sha(repo/'src/nes'/name)==digest,name
 out.mkdir(parents=True)
 for name in cm['sources']:
  q=out/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(core/name,q)
 for name in tm['sources']:shutil.copyfile(repo/'src/nes'/name,out/name)
 declarations=['input wire clk','input wire host_clk'];connections=[];virtual=[]
 for module,prefix,source in [('nes_resource','nes',(out/'nes_resource.sv').read_text()),('nes_transport','transport',(out/'nes_transport.sv').read_text())]:
  conn=[]
  for direction,width,name in ports(source,module):
   signal='clk' if name in ('clk','queue_clk') else 'host_clk' if name=='host_clk' else prefix+'_'+name
   if signal not in ('clk','host_clk'):
    declarations.append(f'{direction} wire {width} {signal}');virtual.append(signal)
   conn.append('.'+name+'('+signal+')')
  connections.append(module+' '+prefix+'('+','.join(conn)+');')
 wrapper='// Resource-only co-placement. Producer pins are external; no encoder is implied.\nmodule nes_joint_resource(\n'+',\n'.join(declarations)+'\n);\n'+'\n'.join(connections)+'\nendmodule\n'
 (out/'nes_joint_resource.sv').write_text(wrapper,newline='\n')
 (out/'joint.qpf').write_text('PROJECT_REVISION = "joint"\n')
 (out/'joint.sdc').write_text('create_clock -name nes_queue -period 46.560846 [get_ports clk]\ncreate_clock -name host -period 11.904762 [get_ports host_clk]\nderive_clock_uncertainty\n')
 lines=(core/'probe.qsf').read_text().splitlines()
 qsf=[line for line in lines if not any(s in line for s in ['TOP_LEVEL_ENTITY','SDC_FILE','VIRTUAL_PIN','SEED'])]
 qsf += ['set_global_assignment -name TOP_LEVEL_ENTITY nes_joint_resource','set_global_assignment -name SDC_FILE joint.sdc','set_global_assignment -name SEED '+str(a.seed)]
 qsf += ['set_global_assignment -name SYSTEMVERILOG_FILE '+name for name in list(tm['sources'])+['nes_joint_resource.sv']]
 qsf += ['set_instance_assignment -name VIRTUAL_PIN ON -to '+name for name in virtual]
 (out/'joint.qsf').write_text('\n'.join(qsf)+'\n')
 m={'candidate':'NES-R1-JOINT-RESOURCE-032','implementation_candidate':'NES-P2-RDY-014','transport_candidate':'NES-H1-SNES-FRONTEND-031','hardware_eligible':False,
 'seed':a.seed,'driver_sha256':sha(__file__),'core_reference_sha256':sha(core/'result.json'),'transport_reference_sha256':sha(repo/'analysis/local-snes-frontend-031/resource/result.json'),
 'sources':{name:sha(out/name) for name in list(cm['sources'])+list(tm['sources'])+['nes_joint_resource.sv','joint.qpf','joint.qsf','joint.sdc']},'phases':{},
 'scope':'Unchanged018 core+12KiBRAM and031 transport in one top,sharedNES/queueclock,external producer inputs. No actual encoder/producer/memoryservice/PLL/loader/boardIO. Virtual pins and area-only fit; no STA signoff or functional integration claim.'}
 for phase in ('map','fit'):
  with (out/(phase+'.log')).open('wb') as log:
   proc=subprocess.run([str(a.quartus_bin/('quartus_'+phase+'.exe')),'joint'],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=600)
  m['phases'][phase]=proc.returncode;(out/'result.json').write_text(json.dumps(m,indent=2)+'\n')
  print(phase,proc.returncode,flush=True)
  if proc.returncode:raise SystemExit('Inspect '+str(out/(phase+'.log')))
 print((out/'output_files/joint.fit.summary').read_text(encoding='latin-1'),flush=True)
if __name__=='__main__':main()
