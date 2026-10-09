# SPDX-License-Identifier: MIT
"""Changed RAM bridge/frontend resets with synthetic byte fixtures and actual RTL."""
from pathlib import Path
import argparse,json,re,os,shutil,subprocess
from nes_reset124 import ROOT,bridge,transport,put,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--baseline',type=Path)
 a=p.parse_args();o=a.out.resolve();assert str(o).isascii() and not o.exists();o.mkdir()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 names=['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_snes_frontend','nes_transport']
 # The core/fit uses the pinned044 frontend carried by052, not the older031
 # public module with the same filename. Require that exact source inventory.
 history=json.loads((ROOT/'analysis/rom-physical-artifacts.json').read_bytes());prefix='analysis/local-rom-physical-052/live/'
 pins={v['path'][len(prefix):]:v['sha256'] for rows in history.values() if isinstance(rows,list) for v in rows if isinstance(v,dict) and v.get('path','').startswith(prefix)}
 for n in names:
  filename=n+'.sv';assert sha(a.baseline/filename)==pins[filename],filename
  shutil.copy2(a.baseline/filename,o/filename)
 for n in ['packet_cdc_tb','snes_frontend_tb','reset124_tb']:shutil.copy2(ROOT/'tests/nes-functional'/(n+'.sv'),o/(n+'.sv'))
 shutil.copy2(ROOT/'src/nes/diagnostic/nes_domain_reset124.sv',o/'nes_domain_reset124.sv')
 shutil.copy2(__file__,o/'executed-driver.py');shutil.copy2(ROOT/'tools/nes_reset124.py',o/'executed-reset124.py')
 for n,fn in [('nes_packet_cdc_ram.sv',bridge),('nes_transport.sv',transport)]:put(o/n,fn((o/n).read_text()))
 put(o/'packet_cdc_tb.sv',(o/'packet_cdc_tb.sv').read_text().replace('nes_packet_cdc dut','nes_packet_cdc_ram dut').replace('three_actual_packet_payloads','three_synthetic_packet_payloads'))
 # 044 qualifies two agreeing active samples, one edge later than031.
 # Keep the existing120ns response deadline and every data/abort assertion;
 # replace only the obsolete031 five-edge bound with the044 six-edge bound.
 # 044 also records release without a response after an overread: missing
 # response bit8 plus premature-release bit1. Preserve both, expect9, not031's8.
 put(o/'snes_frontend_tb.sv',(o/'snes_frontend_tb.sv').read_text().replace(' nes_transport transport(.*);',' wire [127:0] frontend_snapshot;\n nes_transport transport(.*);').replace('latency>5*(hhalf*2)+1','latency>6*(hhalf*2)+1').replace("rd(24'h00600a,8,0,180)","rd(24'h00600a,9,0,180)"))
 for i,(n,count) in enumerate([('split',2328),('sprite',2052),('resident',2008)]):put(o/(n+'.hex'),''.join(f'{(j*17+i*29)&255:02x}\n' for j in range(count)))
 m=dict(candidate='NES-DOMAIN-RESET-124-TRANSPORT',passed=False,sources={p.name:sha(p) for p in o.iterdir()},runs={},scope='Actual RAM bridge/host stage/frontend. Synthetic byte arrays, logical SNES bus. Not game frames or electrical timing.')
 def save():put(o/'result.json',json.dumps(m,indent=2)+'\n')
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert r.returncode==0,label
  return (o/(label+'.log')).read_text(errors='replace')
 def sim(tb,args,label,expected):
  text=run('vsim',['-c',tb,*args,'-do','onerror {quit -code 1}; run -all; quit -f'],label)
  assert expected in text and '** Fatal:' not in text,label
  m['runs'][label]={'pass':True,'summary':[line for line in text.splitlines() if 'PASS ' in line]};save()
 save();run('vlib',['work'],'vlib')
 run('vlog',['-sv',*[n+'.sv' for n in names],'nes_domain_reset124.sv','packet_cdc_tb.sv','snes_frontend_tb.sv','reset124_tb.sv'],'compile')
 sim('reset124_tb',[],'reset-contract','PASS RESET124')
 for q,h,phase in [(5,7,3),(7,5,1),(5,11,9)]:
  label=f'bridge-{q}-{h}-{phase}'
  sim('packet_cdc_tb',[f'+QHALF={q}',f'+HHALF={h}',f'+HPHASE={phase}',f'+TRACE={label}.tsv'],label,'PASS NES PACKET CDC checks=13')
 sim('snes_frontend_tb',['+QHALF=23.280423','+HHALF=5.952381','+HPHASE=1.1','+TRACE=frontend.tsv'],'frontend','PASS NES SNES FRONTEND checks=13')
 # Validate the adapted044 contract against the unmodified pinned044/052
 # frontend+transport as well; this is not a relaxation to hide a reset change.
 for n in names:shutil.copy2(a.baseline/(n+'.sv'),o/('baseline-'+n+'.sv'))
 run('vlib',['baseline_work'],'baseline-vlib')
 run('vlog',['-work','baseline_work','-sv',*['baseline-'+n+'.sv' for n in names],'snes_frontend_tb.sv'],'baseline-compile')
 sim('snes_frontend_tb',['-lib','baseline_work','+QHALF=23.280423','+HHALF=5.952381','+HPHASE=1.1','+TRACE=baseline-frontend.tsv'],'baseline-frontend','PASS NES SNES FRONTEND checks=13')
 # A raw-reset bypass must fail the no-early-release observation contract.
 s=(o/'nes_domain_reset124.sv').read_text().replace('assign reset=release_reset[1];','assign reset=raw_reset;')
 put(o/'negative-bypass.sv',s);run('vlog',['-sv','negative-bypass.sv'],'negative-compile')
 text=run('vsim',['-c','reset124_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'negative-bypass')
 assert '** Fatal: RESET124 contract' in text and 'PASS RESET124' not in text
 m.update(passed=True,raw_bypass_rejected=True);save();print('PASS124 reset/bridge/frontend + raw bypass rejection')
if __name__=='__main__':main()
