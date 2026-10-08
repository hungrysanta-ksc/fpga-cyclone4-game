# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,os,re,shutil,sys
from nes_spi_boot import ROOT,sha,put,run
from nes_clock_reset086 import materialize

def main():
 p=argparse.ArgumentParser()
 for n in ['out','host-run','questa-bin','fpga-evidence']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 host=a.host_run.resolve();h=json.loads((host/'result.json').read_bytes());assert h['candidate']=='NES-CF86-FAULT-CAPTURE-095'
 for n,v in h['files'].items():assert sha(host/n)==v,n
 meta=json.loads((ROOT/'analysis/clock086-verification.json').read_bytes());assert sha(a.fpga_evidence/'manifest.json')==meta['manifest_sha256']
 fit=json.loads((a.fpga_evidence/'fit03/result.json').read_bytes());out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 files=materialize(out);production={n:sha(out/n) for n in files}
 for n,v in production.items():assert fit['sources'][n]==v,n
 shutil.copy2(__file__,out/'executed-fault-replay.py')
 put(out/'pll_model.sv',"`timescale 1ns/1ps\nmodule gbc_bus_pll0(input areset,inclk0,output reg c0=0,output wire locked);reg enable=1;always #5.952381 if(enable)c0=~c0;assign locked=1'b0;endmodule\n")
 model=(ROOT/'tests/nes-functional/rom_boot_model.sv').read_text().replace('assign #25','assign #(70,70,35)').replace('<35.70','<350');put(out/'rom_boot_model.sv',model)
 shutil.copy2(ROOT/'tests/nes-functional/session095_fault_tb.sv',out/'session095_fault_tb.sv');files+=['pll_model.sv','rom_boot_model.sv','session095_fault_tb.sv']
 run([sys.executable,'-B',ROOT/'tools/build_nes_h1_board.py','--out',out/'h1'],out,'fixture')
 for n in ['h1-pattern.hex','h1-program.hex']:shutil.copy2(out/'h1/build'/n,out/n)
 for tool,args in [('vlib',['work']),('vlog',['-sv',*files])]:run([a.questa_bin/(tool+'.exe'),*args],out,tool)
 cases=[]
 for case,negative in [('101',False),('106',False),('101',True)]:
  assert sha(host/(case+'.trace'))==h['cases'][case]['trace_sha256'];shutil.copy2(host/(case+'.trace'),out/'fault.trace')
  name=case+('-negative' if negative else '')
  try:log=run([a.questa_bin/'vsim.exe','-c','-voptargs=-O5','session095_fault_tb','+KEEP_LOCK='+str(int(negative)),'-do','onerror {quit -code 1}; run -all; quit -f'],out,name,120)
  except RuntimeError:
   if not negative:raise
   log=(out/(name+'.log')).read_text(errors='replace')
  if negative:assert '** Fatal:' in log and '095 raw fault did not match C READY-low premise' in log
  else:assert 'PASS095 FAULT' in log and '** Fatal:' not in log
  cases.append(dict(case=case,negative=negative,log_sha256=sha(out/(name+'.log')),marker=next(x for x in log.splitlines() if ('** Fatal:' if negative else 'PASS095 FAULT') in x)))
 (out/'result.json').write_text(json.dumps(dict(candidate='NES-CF86-FAULT-REPLAY-095',cases=cases,production_sources=production,host_result_sha256=sha(host/'result.json'),physical=False,closed_loop_cosimulation=False,raw_lock_fault_only=True),indent=2)+'\n');print(json.dumps(cases))
if __name__=='__main__':main()
