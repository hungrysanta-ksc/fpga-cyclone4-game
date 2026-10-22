# SPDX-License-Identifier: MIT
"""Actual ARM packets through shared display RAM; independent C and H2 oracle."""
from pathlib import Path
import argparse,json,os,shutil
from nes_delta231 import BASE,ROOT,sha,once
from nes_joint266 import sources
from probe_nes_joint265 import prepare as prior_prepare,tb as prior_tb,run


def tb():
 s=prior_tb().replace('joint265_tb','joint266_tb').replace('nes_joint265 dut','nes_joint266 dut')
 s=once(s,'dut.core.ram_a_addr>817','dut.core.ram_a_addr>817&&!(dut.core.encoder.state==dut.core.encoder.D_CHECK&&dut.core.ram_a_addr>=864&&dut.core.ram_a_addr<=867)')
 s=once(s,'v_sealed&&dut.flow.state==dut.flow.IDLE','v_sealed&&(dut.flow.state==dut.flow.IDLE||dut.flow.state==dut.flow.DREQ||dut.flow.state==dut.flow.DWAIT||dut.flow.state==dut.flow.DPRESENT)')
 s=once(s,'reg [7:0] expected_display265[0:23];','reg [7:0] expected_display265[0:23];reg [7:0] display_expected266;integer display_polls266=0;')
 s=once(s,'for(integer j=0;j<24;j++)begin', '''for(integer j=0;j<12;j++)begin
     val263=0;
     while(!val263)begin rd261(24'h006054,val263);display_polls266++;end
     case(j)
      0:display_expected266={7'd0,~serial[0]};
      1:display_expected266=expected_display265[18];
      2:display_expected266=expected_display265[22];
      3:display_expected266=prelude262[30];4:display_expected266=prelude262[31];
      5:display_expected266=prelude262[32];6:display_expected266=prelude262[33];7:display_expected266=prelude262[34];
      default:display_expected266=expected_display265[j+4];
     endcase''')
 s=once(s,'val263!==expected_display265[j]', 'val263!==display_expected266')
 s=once(s,'    token261(dut.flow.last_map_token);wr261', '''    for(integer j=0;j<4;j++)if(dut.core.memory[864+j]!==expected_display265[12+j])$fatal(1,"phase offsets266");
    $fwrite(events261,"display266,%0d,%0d,%0d\\n",f,display_reads265,display_polls266);
    token261(dut.flow.last_map_token);wr261''')
 s=s.replace('PASS JOINT265','PASS JOINT266')
 return s


def prepare(d,last):
 src,pins,stats=prior_prepare(d,last);src.pop('nes_joint265.sv')
 for n,s in sources().items():(d/n).write_text(s,encoding='utf-8',newline='\n');src[n]=''
 (d/'joint266_tb.sv').write_text(tb(),encoding='utf-8',newline='\n')
 for name in ['nes_joint266.py','probe_nes_joint266.py']:
  path=ROOT/'tools'/name;shutil.copyfile(path,d/name);pins[path.relative_to(BASE).as_posix()]=sha(path)
 return src,pins,stats


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);p.add_argument('--last',type=int,default=975);a=p.parse_args()
 d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 src,pins,stats=prepare(d,a.last)
 run('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',['-O2','-std=c99','-Wall','-Wextra','-Werror','-shared','nes_producer264.c','-o','producer263.dll'],d,'native')
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*src,'joint266_tb.sv'],d,'vlog')
 log=run(a.questa_bin/'vsim.exe',['-c','-sv_lib','producer263','work.joint266_tb',f'+LAST={a.last}','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',1800)
 assert f'PASS JOINT266 frames={a.last-904}' in log
 r=dict(passed=True,frames=a.last-904,rtl_hashes={n:sha(d/n) for n in src},input_hashes=pins,scope=__doc__,actual_SNES=False,full_ARM=False,physical=False,whole_FIT=False)
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(log[-1500:])


if __name__=='__main__':main()
