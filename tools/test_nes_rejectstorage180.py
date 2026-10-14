# SPDX-License-Identifier: MIT
"""Real SPI history plus first-fault takeover of shared context storage."""
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
    s=replace(s,' wire sample_enable;wire [95:0] sample;\n nes_reject_witness180 witness(.*);', ''' wire sample_enable=observer.history_emit180;
 wire [95:0] sample={valid?2'd2:2'd1,generation[7:0],final_errors,scanline,dot,mask,
 rows,groups,objects,exceptions,palettes[5]?5'd31:palettes[4:0]};''')
    s=replace(s,'.history_enable180(sample_enable),', '.history_owned180(owned),.history_release180(release_frame),.history_collecting180(collecting),.history_live_errors180(live_errors),')
    s=replace(s,'  spi(8\'ha2);', '''  spi(8'h74);if(page!==56'he5016082080028)$fatal(1,"PPU context upper takeover %h",page);
  spi(8'h75);if(page!==56'he5016060600201)$fatal(1,"PPU context lower takeover %h",page);
  // After the fault, arbitrary new owner/error inputs must not change context.
  active=1;owned=0;@(negedge clk);owned=1;live_errors=25'h1ffffff;final_errors=25'h1ffffff;
  repeat(5)@(negedge clk);spi(8'h74);if(page!==56'he5016082080028)$fatal(1,"fault context overwritten");
  active=0;
  spi(8'ha2);''')
    # Also exercise a fault before arming and simultaneous core STOP/fault.
    s=replace(s,'  $display("PASS180 witness', '''  for(integer z=0;z<2;z++)begin
   boot();fault=1;active=(z==0);@(negedge clk);fault=0;active=0;repeat(3)@(negedge clk);
   spi(8'h74);if(page!==56'he5016082080028)$fatal(1,"early/STOP fault priority");
   spi(8'h75);if(page!==56'he5016060600201)$fatal(1,"early/STOP fault tail");
  end
  $display("PASS180 witness''')
    (a.out/'reject180_tb.sv').write_text(s,encoding='utf8',newline='\n')
    files=re.findall(r'-name (?:SYSTEMVERILOG|VERILOG)_FILE (\S+)',(a.out/'board.qsf').read_text());logs={}
    for exe,args,label in [('vlib',['work'],'vlib'),('vlog',['-sv','-mfcu',*files,'reject180_tb.sv'],'vlog'),
      ('vsim',['-c','work.reject180_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'history')]:
        with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
        text=(a.out/(label+'.log')).read_text(errors='replace')
        assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-3000:]
        logs[label]=sha(a.out/(label+'.log'))
    assert 'PASS180 witness' in text
    result=dict(passed=True,sources=m['sources'],logs=logs,public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_rejectstorage180.py','tests/nes-functional/reject180_tb.sv']},generated_tb_sha256=sha(a.out/'reject180_tb.sv'),scope=__doc__,physical=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS STORAGE180 actual SPI/history/fault takeover')


if __name__=='__main__':main()
