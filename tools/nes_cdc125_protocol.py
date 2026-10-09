# SPDX-License-Identifier: MIT
"""Observe125 capture/overwrite windows on exact124 RTL; two early-use controls."""
from pathlib import Path
import argparse,json,os,re,subprocess,shutil
from nes_cdc125_sta import ROOT,sha,put
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.baseline;o=a.out.resolve();assert not o.exists() and str(o).isascii()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 meta=json.loads((ROOT/'analysis/reset124-verification.json').read_bytes());assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];o.mkdir();inputs={}
 for folder,names in [('unit01',['nes_rom_physical.sv','rom_physical_model.sv','rom_physical_tb.sv']),('transport04',['nes_packet_cdc_ram.sv','nes_packet_queue_ram.sv','packet_cdc_tb.sv','split.hex','sprite.hex','resident.hex'])]:
  for n in names:
   k=folder+'/'+n;assert sha(e/k)==pins[k],k;shutil.copy2(e/k,o/n);inputs[k]=pins[k]
 for n in ['nes_rom_physical.sv','nes_packet_cdc_ram.sv','nes_packet_queue_ram.sv']:assert sha(o/n)==pins['fit01/'+n]
 for kind in ['reader','bridge']:shutil.copy2(ROOT/f'tests/nes-functional/cdc125_{kind}.svh',o/f'cdc125_{kind}.svh')
 s=(o/'rom_physical_tb.sv').read_text().replace('#23.280423','#22.727')
 s=s.replace('endmodule',(o/'cdc125_reader.svh').read_text()+'\nendmodule').replace('  $display("PASS PHYSICAL','  $display("CDC125 reader address=%0f data=%0f checks=%0d/%0d hold=%0d",min_address125,min_data125,address_checks125,data_checks125,hold_checks125);\n  $display("PASS PHYSICAL')
 put(o/'rom_physical_tb.sv',s)
 s=(o/'packet_cdc_tb.sv').read_text().replace('integer qhalf=5,hhalf=7,hphase=3,unused;','realtime qhalf=22.727,hhalf=5.952,hphase=1.1;integer unused;').replace('QHALF=%d','QHALF=%f').replace('HHALF=%d','HHALF=%f').replace('HPHASE=%d','HPHASE=%f')
 s=s.replace('endmodule',(o/'cdc125_bridge.svh').read_text()+'\nendmodule').replace('  $display("PASS NES PACKET CDC','  $display("CDC125 bridge request=%0f reply=%0f checks=%0d/%0d hold=%0d",min_req125,min_reply125,req_checks125,reply_checks125,hold_checks125);\n  $display("PASS NES PACKET CDC')
 put(o/'packet_cdc_tb.sv',s);shutil.copy2(__file__,o/'executed-protocol125.py')
 m=dict(candidate='NES-CDC-PROTOCOL-125',passed=False,inputs=inputs,sources={f.name:sha(f) for f in o.iterdir()},runs={})
 def save():put(o/'result125.json',json.dumps(m,indent=2)+'\n')
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert r.returncode==0,label
  return (o/(label+'.log')).read_text(errors='replace')
 def sim(tb,args,label,negative=False):
  s=run('vsim',['-c',tb,*args,'-do','onerror {quit -code 1}; run -all; quit -f'],label)
  if negative:assert '** Fatal: CDC125' in s and 'PASS PHYSICAL' not in s and 'PASS NES PACKET CDC' not in s,label
  else:assert 'CDC125 ' in s and '** Fatal:' not in s and ('PASS PHYSICAL' in s or 'PASS NES PACKET CDC' in s),label
  m['runs'][label]=dict(passed=True,negative=negative,summary=[line for line in s.splitlines() if 'CDC125' in line or 'PASS PHYSICAL' in line or 'PASS NES PACKET CDC' in line]);save()
 save();run('vlib',['work'],'vlib');run('vlog',['-sv','nes_rom_physical.sv','rom_physical_model.sv','rom_physical_tb.sv','nes_packet_queue_ram.sv','nes_packet_cdc_ram.sv','packet_cdc_tb.sv'],'compile')
 for phase in [0,3500]:sim('rom_physical_tb',[f'+PHASE_PS={phase}'],f'reader-{phase}')
 for phase in [0.1,1.1,5.5]:sim('packet_cdc_tb',[f'+HPHASE={phase}',f'+TRACE=bridge-{phase}.tsv'],f'bridge-{phase}')
 s=(o/'nes_rom_physical.sv').read_text();assert s.count('request_sync[1]!=ack_toggle')==1
 put(o/'reader-early.sv',s.replace('request_sync[1]!=ack_toggle','request_sync[0]!=ack_toggle'));run('vlog',['-sv','reader-early.sv'],'reader-negative-compile');sim('rom_physical_tb',['+PHASE_PS=3500'],'reader-early',True)
 s=(o/'nes_packet_cdc_ram.sv').read_text();assert s.count('if(req_sync[1]!=ack_toggle)')==1
 put(o/'bridge-early.sv',s.replace('if(req_sync[1]!=ack_toggle)','if(req_sync[0]!=ack_toggle)'))
 # Observe actual phase transition/captured command for the early-use control.
 s=(o/'packet_cdc_tb.sv').read_text().replace('dut.phase==0 && dut.req_sync[1]!=dut.ack_toggle','dut.phase==0 && dut.req_sync[0]!=dut.ack_toggle');put(o/'bridge-early-tb.sv',s)
 run('vlog',['-sv','bridge-early.sv','bridge-early-tb.sv'],'bridge-negative-compile');sim('packet_cdc_tb',['+HPHASE=1.1','+TRACE=negative.tsv'],'bridge-early',True)
 m['passed']=True;save();print('PASS125 launch/capture/overwrite observations + two early-use rejections')
if __name__=='__main__':main()
