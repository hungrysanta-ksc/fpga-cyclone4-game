# SPDX-License-Identifier: MIT
"""Run the established OAM comparison using the installed Altera RAM model."""
from pathlib import Path
import argparse,json,subprocess,sys
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','out','questa-bin','altera-mf']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(exist_ok=False)
 old=(ROOT/'tools/test_nes_oamread181.py').read_text()
 old=old.replace("a.out.mkdir(exist_ok=False)","a.out.mkdir(exist_ok=False)")
 old=old.replace("text=text.replace('always @(negedge clk)','always @(posedge clk)')",
  "text=text.replace('always @(negedge clk)','always @(posedge clk)').replace('.clock1(~clk)','.clock1(clk)')")
 anchor="(d/'oam_banked_tb.sv').write_text(bench,encoding='utf8',newline='\\n')"
 assert old.count(anchor)==1
 old=old.replace(anchor,anchor+"\n  shutil.copy2(Path("+repr(str(a.altera_mf))+"),d/'altera_mf.v')")
 old=old.replace("['-sv','-mfcu','regs_savestates.sv'","['-sv','-mfcu','altera_mf.v','regs_savestates.sv'")
 job=a.out/'executed_runner.py';job.write_text(old,encoding='utf8',newline='\n')
 args=[sys.executable,'-B','-X','utf8',str(job)]
 for n in ['baseline','prepared','questa_bin']:args+=['--'+n.replace('_','-'),str(getattr(a,n))]
 args+=['--out',str(a.out/'runs')]
 import os
 env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'tools')
 with (a.out/'runner.log').open('wb') as f:r=subprocess.run(args,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=240)
 assert r.returncode==0,(a.out/'runner.log').read_text(errors='replace')[-4000:]
 result=json.loads((a.out/'runs/result.json').read_bytes())
 result.update(wrapper_sha256=sha(Path(__file__)),altera_mf_sha256=sha(a.altera_mf),
  reference_runner_sha256=sha(ROOT/'tools/test_nes_oamread181.py'),primitive_model=True)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
