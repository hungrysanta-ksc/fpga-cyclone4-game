# SPDX-License-Identifier: MIT
"""Execute full SPI event fixture plus explicit RAM feedback latency hazards."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
from nes_reject180 import replace


def main():
    p=argparse.ArgumentParser()
    for n in ['candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    assert not a.out.exists();a.out.mkdir(parents=True)
    m=json.loads((a.candidate/'preparation.json').read_bytes())
    for n,h in m['sources'].items():
        assert sha(a.candidate/n)==h,n
        (a.out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.candidate/n,a.out/n)
    s=(ROOT/'tests/nes-functional/reject180_tb.sv').read_text()
    s=replace(s,'wire sample_enable;', 'wire feedback_ready180;wire [24:0] feedback_errors180;wire sample_enable;')
    s=replace(s,'.history_sample157(sample),','.feedback_ready180(feedback_ready180),.feedback_errors180(feedback_errors180),.history_sample157(sample),')
    s=replace(s,'  begin_frame(5);', '''  // Explicit unavailable-feedback injection: same error MUST emit, not be lost.
  begin_frame(40);error_at(25'h80000,193,19,0);final_errors=25'h88200;
  force feedback_ready180=0;seal(0,1,193,19,0);release feedback_ready180;
  begin_frame(5);''')
    (a.out/'reject180_tb.sv').write_text(s,encoding='utf8',newline='\n')
    extra='tests/nes-functional/rejectram180_feedback_tb.sv';shutil.copy2(ROOT/extra,a.out/Path(extra).name)
    files=re.findall(r'-name (?:SYSTEMVERILOG|VERILOG)_FILE (\S+)',(a.out/'board.qsf').read_text())
    logs={}
    def run(exe,args,label):
        with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
        s=(a.out/(label+'.log')).read_text(errors='replace')
        assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-3000:]
        logs[label]=sha(a.out/(label+'.log'));return s
    run('vlib',['work'],'vlib');run('vlog',['-sv','-mfcu',*files,'reject180_tb.sv',Path(extra).name],'vlog')
    for top,marker in [('reject180_tb','PASS180 witness'),('rejectram180_feedback_tb','PASS RAM180 feedback')]:
        s=run('vsim',['-c','work.'+top,'-do','onerror {quit -code 1}; run -all; quit -f'],top)
        assert marker in s;print(marker,flush=True)
    result=dict(passed=True,sources=m['sources'],logs=logs,public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_rejectram180.py','tests/nes-functional/reject180_tb.sv',extra]},generated_tb_sha256=sha(a.out/'reject180_tb.sv'),scope=__doc__,physical=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
