# SPDX-License-Identifier: MIT
"""Stop with8 H2 bytes committed and the next CDC byte pending; same RTL."""
import argparse,json,os,re
from pathlib import Path
from nes_delta231 import sha,once
from probe_nes_joint262 import prepare,run


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
 d=a.out.resolve();assert not d.exists() and d.as_posix().isascii() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 src,pins,stats=prepare(d,905)
 f=d/'joint262_tb.sv';s=f.read_text()
 s=once(s,'if(PRENEG==5)begin wait(dut.context_valid);@(negedge clk);test_abort=1;end',
 'if(PRENEG==5)begin wait(context_bytes262==8);@(negedge clk);wait(dut.context_valid);@(negedge clk);test_abort=1;end')
 f.write_text(s,encoding='utf-8',newline='\n')
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*src,'joint262_tb.sv'],d,'vlog')
 log=run(a.questa_bin/'vsim.exe',['-c','work.joint262_tb','-gPRENEG=5','+LAST=905','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim')
 assert 'PASS JOINT262 PRENEG=5 context=8 begins=0' in log
 r=dict(passed=True,context_bytes_before_STOP=8,BEGIN_count=0,RAM_frozen_bytes=1024,rtl_hashes={n:sha(d/n) for n in src},input_hashes=pins,TB_sha256=sha(f),scope=__doc__)
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n');print(log[-500:])


if __name__=='__main__':main()
