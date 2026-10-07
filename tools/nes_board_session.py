# SPDX-License-Identifier: MIT
"""063 complete062 C menu traces; production C and061 RTL stay unchanged."""
from pathlib import Path
import argparse,json,shutil
from nes_menu_diagnostic import materialize,host_source,replace
from nes_mcu_loader import ROOT,sha,run
from build_nes_video_workloads import build

def platform():
 s=host_source()
 a=s.index('static void record(int expect) {');b=s.index('unsigned NVIC_GetEnableIRQ',a)
 capture=r'''static FILE *session_trace;
static unsigned trace_ss,trace_sck,trace_mosi,trace_bits,trace_samples,trace_frames;
static unsigned long long trace_start;
static uint8_t trace_tx[8],trace_rx[8];
static unsigned long long pack8(const uint8_t *p) {
 unsigned long long v=0;for(unsigned i=0;i<8;i++)v=(v<<8)|p[i];return v;
}
static void record(int expect) {
 if(!session_trace)return;
 unsigned ss=!!(mock_a.ODR&16),sck=!!(mock_b.ODR&8),mosi=!!(mock_b.ODR&32);
 if(!ss&&mosi!=trace_mosi) {
  assert(!sck&&trace_samples==trace_bits);
  assert(ns-trace_start==2000ull+trace_bits*4000ull+(trace_bits/8)*2000ull);
 }
 if(ss!=trace_ss) {
  if(!ss){assert(!sck);trace_start=ns;trace_bits=trace_samples=0;memset(trace_tx,0,8);memset(trace_rx,0,8);}
  else {
   assert(trace_bits==16||trace_bits==64);assert(trace_samples==trace_bits&&!sck);
   assert(ns-trace_start==4000ull+trace_bits*4000ull+(trace_bits/8)*2000ull);
   fprintf(session_trace,"%llu %llu %u %016llx %016llx\n",trace_start,ns,trace_bits,pack8(trace_tx),pack8(trace_rx));
   trace_frames++;
  }
 }
 if(!ss&&sck!=trace_sck) {
  if(sck) {
   unsigned bit=trace_bits;assert(bit<64);
   assert(ns-trace_start==4000ull+bit*4000ull+(bit/8)*2000ull);
   trace_tx[bit/8]|=(uint8_t)(!!(mock_b.ODR&32)<<(7-bit%8));trace_bits++;
  } else assert(trace_samples==trace_bits);
 }
 if(expect!=-1) {
  unsigned bit=trace_samples;assert(!ss&&sck&&bit<trace_bits);
  assert(ns-trace_start==6000ull+bit*4000ull+(bit/8)*2000ull);
  trace_rx[bit/8]|=(uint8_t)(!!(mock_b.IDR&16)<<(7-bit%8));trace_samples++;
 }
 trace_ss=ss;trace_sck=sck;trace_mosi=mosi;
}
'''
 return s[:a]+capture+s[b:]

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True);a=p.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);materialize(out)
 shutil.copy2(__file__,out/'executed-driver.py')
 (out/'session-platform.c').write_text(platform(),encoding='utf-8',newline='\n')
 for n in ['mcu_loader_platform.h','board_session_host.c']:shutil.copy2(ROOT/'tests/nes-functional'/n,out/n)
 for n in ['config','bits','timer','snes','fpga','fpga_spi','fileops','uart']:(out/(n+'.h')).write_text('#include "mcu_loader_platform.h"\n')
 fixtures={c:build(out/c,c) for c in ['fine_x','banks32']}
 run([a.gcc,'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-Wall','-Wextra','-Werror','-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
  'nes_rom_spi.c','nes_rom_verify.c','nes_h1_stm32.c','nes_h1_session.c','nes_menu_diagnostic.c','board_session_host.c','-o','host.exe'],out,'compile')
 log=run([out/'host.exe',out/'fine_x/mmc3.nes',out/'banks32/mmc3.nes',out/'fine_x.trace',out/'banks32.trace'],out,'host')
 assert 'PASS SESSION C bytes=81920' in log and 'PASS SESSION C bytes=98304' in log
 r=dict(candidate='NES-BOARD-SESSION-063',host_pass=True,production_candidate='NES-MENU-DIAGNOSTIC-062',actual_stm32_execution=False,
  sources={f.name:sha(f) for f in sorted(out.iterdir()) if f.suffix in ['.c','.h']},
  fixtures={c:m['sha256'] for c,m in fixtures.items()},traces={c:sha(out/(c+'.trace')) for c in fixtures},driver_sha256=sha(out/'executed-driver.py'))
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
 print('\n'.join(line for line in log.splitlines() if line.startswith('PASS SESSION C')))

if __name__=='__main__':main()
