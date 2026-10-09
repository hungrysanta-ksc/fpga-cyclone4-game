# SPDX-License-Identifier: MIT
"""Recheck actual131 reader capture windows; reuse only byte-identical bridge125."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_cdc125_sta import ROOT,sha,put

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out.resolve();assert not o.exists() and str(o).isascii()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 archives={};pins={}
 for tag,folder in [('cdc125','nes-cdc125'),('counter131','nes-counter131')]:
  e=a.baseline/folder/'evidence';m=json.loads((ROOT/f'analysis/{tag}-verification.json').read_bytes())
  assert sha(e/'manifest.json')==m['manifest_sha256'];archives[tag]=e;pins[tag]=json.loads((e/'manifest.json').read_bytes())['files']
 o.mkdir();inputs={}
 def copy(tag,relative,name):
  e=archives[tag];h=pins[tag][relative];assert sha(e/relative)==h
  shutil.copy2(e/relative,o/name);inputs[tag+'/'+relative]=h
 copy('counter131','fit05/nes_rom_physical.sv','nes_rom_physical.sv')
 for n in ['rom_physical_model.sv','rom_physical_tb.sv']:copy('cdc125','protocol01/'+n,n)
 # Prior bridge protocol observations remain applicable only to exact same RTL.
 bridge={}
 for n in ['nes_packet_cdc_ram.sv','nes_packet_queue_ram.sv']:
  old=archives['cdc125']/'protocol01'/n;new=archives['counter131']/'fit05'/n
  assert sha(old)==pins['cdc125']['protocol01/'+n]==sha(new)==pins['counter131']['fit05/'+n]
  bridge[n]=sha(new)
 prior=archives['cdc125']/'protocol01/result125.json'
 assert sha(prior)==pins['cdc125']['protocol01/result125.json'] and json.loads(prior.read_bytes())['passed']
 shutil.copy2(ROOT/'tests/nes-functional/cdc125_reader.svh',o/'cdc125_reader.svh')
 s=(o/'rom_physical_tb.sv').read_text()
 assert s.count('endmodule')==1 and '.READ_CYCLES(16)' in s and '#22.727' in s
 assert (o/'cdc125_reader.svh').read_text() in s
 s=s.replace('CDC125 reader address=%0f','CDC132 reader address=%0f')
 put(o/'rom_physical_tb.sv',s);shutil.copy2(__file__,o/'executed-protocol132.py')
 m=dict(candidate='NES-CDC-PROTOCOL-132',passed=False,inputs=inputs,bridge_reused=bridge,bridge_result_sha256=sha(prior),sources={f.name:sha(f) for f in o.iterdir()},runs={})
 def save():put(o/'protocol132.json',json.dumps(m,indent=2)+'\n')
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert r.returncode==0,label
  return (o/(label+'.log')).read_text(errors='replace')
 def sim(label,phase,negative=False):
  s=run('vsim',['-c','rom_physical_tb',f'+PHASE_PS={phase}','-do','onerror {quit -code 1}; run -all; quit -f'],label)
  if negative:assert '** Fatal: CDC125' in s and 'PASS PHYSICAL' not in s,label
  else:assert 'CDC132 reader' in s and 'PASS PHYSICAL' in s and '** Fatal:' not in s,label
  m['runs'][label]=dict(passed=True,negative=negative,summary=[x for x in s.splitlines() if 'CDC132 reader' in x or 'PASS PHYSICAL' in x or '** Fatal:' in x]);save()
 save();run('vlib',['work'],'vlib');run('vlog',['-sv','nes_rom_physical.sv','rom_physical_model.sv','rom_physical_tb.sv'],'compile')
 for phase in [0,3500]:sim('reader-'+str(phase),phase)
 s=(o/'nes_rom_physical.sv').read_text();assert s.count('request_sync[1]!=ack_toggle')==1
 put(o/'reader-early.sv',s.replace('request_sync[1]!=ack_toggle','request_sync[0]!=ack_toggle'))
 run('vlog',['-sv','reader-early.sv'],'negative-compile');sim('reader-early',3500,True)
 m['passed']=True;save();print('PASS132 actual131 reader two phases + early-capture rejection; identical bridge125 reused')
if __name__=='__main__':main()
