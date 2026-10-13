# SPDX-License-Identifier: MIT
"""Revoke/reset a full FIFO, then verify fresh-generation bytes after restart."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(exist_ok=False)
 shutil.copyfile(a.candidate/'nes_native_fill165.sv',a.out/'nes_native_fill165.sv')
 s=(ROOT/'tests/nes-functional/native_fill165_tb.sv').read_text().replace('module native_fill165_tb;', 'module cancel171_tb;\n reg allow_consume=0;')
 s=s.replace('assign byte_ready=(ticks%5!=0)', 'assign byte_ready=allow_consume && (ticks%5!=0)')
 s=s.replace('wait(model_pending);@(negedge clk);', 'wait(dut.fifo_used==256);@(negedge clk);\n   check(!byte_ready && dut.fifo_valid,"full FIFO retained before cancellation");')
 s=s.replace('check(quarantine&&mem_abort&&!byte_valid&&!mem_request,"cancelled pending request quarantined");','check(!byte_valid&&!mem_request,"queued bytes suppressed on cancellation");\n   allow_consume=1;')
 # Full FIFO has no outstanding backend request; unlike the original fixture,
 # restart is allowed immediately. Pending-response quarantine is tested above.
 s=s.replace('start=1;repeat(2)@(negedge clk);check(!busy,"cannot restart before backend flush");', 'check(mem_idle,"full FIFO has no outstanding backend request");start=1;')
 s=s.replace('PASS FILL165','PASS CANCEL171')
 s=s.replace('ticks<=ticks+1;response<=0;', 'check(dut.fifo_used<=256 || reset,"FIFO occupancy bounded");\n  ticks<=ticks+1;response<=0;')
 (a.out/'cancel171_tb.sv').write_text(s,encoding='utf-8')
 (a.out/'required.hex').write_text(''.join(f'{i%3+1:x}\n' if i<512 else '0\n' for i in range(8192)))
 (a.out/'chr.hex').write_text(''.join(f'{(i*37+i//256)&255:02x}\n' for i in range(131072)))
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=90)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-2500:];return s
 run('vlib',['work'],'vlib');run('vlog',['-sv','nes_native_fill165.sv','cancel171_tb.sv'],'vlog');results=[]
 for mode in [8,9,14]:
  s=run('vsim',['-c','work.cancel171_tb',f'-gMODE={mode}','+REQUIRED=required.hex','+CHR=chr.hex',f'+OUTPUT=case{mode}.tsv','-do','onerror {quit -code 1}; run -all; quit -f'],f'case{mode}')
  results.append(re.search(r'PASS CANCEL171[^\r\n]+',s)[0])
 (a.out/'result.json').write_text(json.dumps(dict(passed=True,results=results,source_sha256=sha(a.candidate/'nes_native_fill165.sv'),testbench_sha256=sha(a.out/'cancel171_tb.sv'),public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_prefetch171_cancel.py','tests/nes-functional/native_fill165_tb.sv']}),indent=2)+'\n');print('PASS171 full FIFO clear/generation/reset')
if __name__=='__main__':main()
