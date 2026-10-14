# SPDX-License-Identifier: MIT
"""Actual SPI ring for reduced episode semantics, cancellation and fault."""
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
    s=replace(s,'first_y,first_x,first_mask,rows,groups,objects,exceptions,',"9'd511,9'd511,mask,rows,groups,objects,exceptions,")
    s=s.replace('016002','016003').replace('seal(0,1,194,1,24);','seal(0,0,194,1,24);').replace('seal(0,1,190,30,0);','seal(0,0,190,30,0);')
    s=replace(s,'   begin_frame(256+k);', '   begin_frame(128+k);seal(1,1,0,0,0);\n   begin_frame(256+k);')
    s=replace(s,'transitions,first-position,seal-counts,jitter,cancel,wrap,SPI,STOP,fault,reset','schema3 episodes,unmeasured-position,final-counts,changed-error-suppression,cancel,wrap,SPI,STOP,fault,reset')
    (a.out/'reject180_tb.sv').write_text(s,encoding='utf8',newline='\n')
    files=re.findall(r'-name (?:SYSTEMVERILOG|VERILOG)_FILE (\S+)',(a.out/'board.qsf').read_text());logs={}
    for exe,args,label in [('vlib',['work'],'vlib'),('vlog',['-sv','-mfcu',*files,'reject180_tb.sv'],'vlog'),('vsim',['-c','work.reject180_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'history')]:
        with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
        text=(a.out/(label+'.log')).read_text(errors='replace')
        assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-3000:]
        logs[label]=sha(a.out/(label+'.log'))
    assert 'PASS180 witness schema3 episodes' in text
    result=dict(passed=True,sources=m['sources'],logs=logs,public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_minreject180.py','tests/nes-functional/reject180_tb.sv']},generated_tb_sha256=sha(a.out/'reject180_tb.sv'),scope=__doc__,physical=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS MINREJECT180 actualSPI schema3 episodes')

if __name__=='__main__':main()
