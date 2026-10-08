# SPDX-License-Identifier: MIT
"""Capture unchanged094 C with explicit synthetic guard cost; not MCU cycles."""
from pathlib import Path
import argparse,json,shutil
from nes_mcu_loader import ROOT,sha
from nes_spi_boot import run
from nes_diag_recovery_checks import function

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True);p.add_argument('--guard-ns',type=int,default=250);a=p.parse_args()
 base=a.baseline.resolve();out=a.out.resolve();assert 0<=a.guard_ns<=2000
 meta=json.loads((ROOT/'analysis/session094-verification.json').read_bytes());assert sha(base.parent/'manifest.json')==meta['manifest_sha256']
 old=json.loads((base/'result.json').read_bytes());assert len(old['cases'])==63
 out.mkdir(parents=True,exist_ok=False)
 for n,h in old['files'].items():
  assert sha(base/n)==h,n
  if Path(n).suffix in ['.c','.h']:shutil.copy2(base/n,out/n)
 for case in ['fine_x','banks32']:shutil.copytree(base/case,out/case)
 header=out/'mcu_loader_platform.h';s=header.read_text();s=s.replace('#define BITBAND(r,b) (((r)>>(b))&1u)','unsigned guard_read095(unsigned,unsigned);\n#define BITBAND(r,b) guard_read095((r),(b))');header.write_text(s)
 platform=out/'platform094.c';s=platform.read_text();oldrecord=function(s,'record')
 capture=(ROOT/'tests/nes-functional/session095_capture.inc').read_text();s=s.replace(oldrecord,capture)
 platform.write_text(s,encoding='utf-8',newline='\n')
 host=(out/'host.c').read_text();host=host[:host.index('int main(')]+'''int main(int argc,char **argv){
 signal(SIGABRT,failed_assert094);assert(argc==4);setvbuf(stdout,0,_IONBF,0);
 FILE *f=fopen(argv[1],"rb");assert(f);original_length=(unsigned)fread(rom,1,sizeof(rom),f);fclose(f);
 initialize(NONE,1);mock_a.IDR=32;guard_ns095=(unsigned)strtoul(argv[3],0,10);
 trace095=fopen(argv[2],"w");assert(trace095);ss095=!!(mock_a.ODR&16);sck095=!!(mock_b.ODR&8);
 struct nes_menu_probe_report r;bool safe=nes_menu_sd_probe("fixture","approved-test-image",original_length==98320,&r);
 assert(safe&&!nes_cf86_failed094()&&r.sd.verified&&r.sd.load.stop_ok&&configs==2);
 assert(!memcmp(loaded,rom+16,original_length-16)&&check_acks==original_length-16&&finishes==1);
 assert(frames095==(original_length-16)*5+16);fclose(trace095);trace095=0;
 printf("PASS095 CAPTURE bytes=%u frames=%u guard_ns=%u guard_reads=%llu time_ns=%llu\\n",original_length-16,frames095,guard_ns095,guard_reads095,ns);return 0;
}
''';(out/'host.c').write_text(host,encoding='utf-8',newline='\n')
 production={n:sha(out/n) for n in meta['host_arm_identical']}
 for n,h in production.items():assert h==meta['host_arm_identical'][n],n
 sources=['nes_rom_spi.c','nes_rom_verify.c','nes_h1_stm32.c','nes_h1_session.c','nes_menu_diagnostic.c','nes_diag_runtime.c','nes_menu_return.c','nes_cf86_session094.c','host.c']
 run([a.gcc,'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-Wall','-Wextra','-Werror','-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',*sources,'-o','host.exe'],out,'compile')
 cases={}
 for case in ['fine_x','banks32']:
  log=run([out/'host.exe',out/case/'mmc3.nes',out/(case+'.trace'),str(a.guard_ns)],out,case,300);assert 'PASS095 CAPTURE' in log
  cases[case]=dict(trace_sha256=sha(out/(case+'.trace')),fixture_sha256=sha(out/case/'mmc3.nes'),marker=log.strip().splitlines()[-1]);print(cases[case]['marker'],flush=True)
 shutil.copy2(__file__,out/'executed-capture.py');shutil.copy2(ROOT/'tests/nes-functional/session095_capture.inc',out/'executed-capture.inc')
 (out/'result.json').write_text(json.dumps(dict(candidate='NES-CF86-REPLAY-095',production_sources=production,cases=cases,guard_ns=a.guard_ns,synthetic_guard_cost=True,actual_mcu=False,files={p.name:sha(p) for p in out.iterdir() if p.suffix in ['.c','.h','.inc','.py']}),indent=2)+'\n')
if __name__=='__main__':main()
