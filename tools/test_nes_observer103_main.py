# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_spi_boot import ROOT,sha
from nes_menu098 import once
from test_nes_menu098 import definition
from test_nes_observer103 import formatter

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence102','arm','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--geometry96',action='store_true');p.add_argument('--uart-stall',action='store_true')
 a=p.parse_args();e=a.evidence102.resolve();s=a.arm.resolve()/'src';o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/quiesce102-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];source=e/('fat32-96-02' if a.geometry96 else 'main02');inputs={}
 def write(n,t):(o/n).write_text(t,encoding='utf-8',newline='\n')
 for f in source.rglob('*'):
  if f.is_file() and f.suffix in ['.c','.h','.inc','.packed','.raw','.bin','.nes']:
   key=f.relative_to(e).as_posix();assert sha(f)==pins[key];inputs[key]=sha(f);dst=o/f.relative_to(source);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
 shutil.copy2(__file__,o/'executed-main103.py');shutil.copy2(ROOT/'tools/test_nes_observer103.py',o/'executed-helper103.py')
 platform=(s/'nes_diag_platform.c').read_text();uart=(s/'stm32f4xx/uart.c').read_text()
 for n in ['nes_diag_platform.c','stm32f4xx/uart.c','printf.c']:shutil.copy2(s/n,o/('production103-'+n.replace('/','-')))
 # Preserve main/load/RTC/SPI/SD inputs and the existing first-error accounting.
 prefix=(o/'host098-prefix.inc').read_text();prefix=once(prefix,'void nes_diag_observe(','void observe_hook103(');write('host098-prefix.inc',prefix)
 q=(o/'quiesce-main102.inc').read_text().replace('assert(steps102<=15);','assert(steps102<100000);').replace('barriers102==3&&steps102==15','steps102>=15&&steps102%15==0&&barriers102*5==steps102')
 write('quiesce-main102.inc',q)
 declarations=platform[platform.index('static volatile unsigned led_phase'):platform.index('uint32_t nes_diag_ticks')]
 observe=definition(platform,'nes_diag_observe').replace('void nes_diag_observe(','static void actual_observe103(')
 write('observer103.inc',declarations+definition(platform,'nes_diag_led_tick')+observe)
 write('uart103.inc','\n'.join(definition(uart,n) for n in ['uart_putc','uart_flush','uart_puts']))
 extra='''
#undef led_pwm
int led_pwmstate,led_rdyledstate,led_readledstate,led_writeledstate;
static void led_std(void){led_pwmstate=0;}
static void led_pwm(void){led_pwmstate=1;}
static struct {unsigned SR,DR;} uart103;
volatile uint32_t nes_diag_uart_dropped;
static unsigned uart_reads103,uart_fault_reads103,observed_fault103;
static unsigned uart_status103(void){
 uart_reads103++;if(nes_return_failed()){uart_fault_reads103++;assert(!"UART sampled after shared fault");}
 return UART_READY103;
}
#define UART_REGS (&uart103)
#define USART_SR_TXE_Pos 7
#undef BITBAND
#define BITBAND(reg,bit) uart_status103()
#include "uart103.inc"
#undef BITBAND
#include "observer103.inc"
void nes_diag_observe(const struct nes_diag_report *r,bool active){
 unsigned before=poll096;
 actual_observe103(r,active);
 if(active&&nes_return_failed()){observed_fault103++;check_quiesce102();assert(poll096==before);}
 observe_hook103(r,active);
}
'''.replace('UART_READY103','0' if a.uart_stall else '1')
 write('observer-main103.inc',extra)
 host=(o/'host102.c').read_text();host=once(host,'static void uart_putc(unsigned c){(void)c;}','');host=once(host,'static void uart_putcrlf(void){}',"static void uart_putcrlf(void){uart_putc('\\n');}")
 for n in ['rdyled','readled','writeled']:
  host=once(host,f'MODEL_VOID({n},(unsigned v))',f'static void {n}(unsigned v){{(void)v;}} /* LED GPIO effects remain modeled. */')
 host=once(host,'#include "quiesce-main102.inc"','#include "quiesce-main102.inc"\n#include "observer-main103.inc"')
 host=once(host,'int main(int argc,char **argv){','#undef printf\nint main(int argc,char **argv){')
 host=once(host,'  assert(terminal102==1);check_quiesce102();','  assert(terminal102==1&&observed_fault103&&!uart_fault_reads103);check_quiesce102();')
 host=host.replace('PASS102','PASS103')
 host='#include <stdio.h>\nint diag_printf(const char *,...);\nvoid uart_putc(char);\n#define printf diag_printf\n'+host
 write('host103.c',host)
 # Only formatter symbols are renamed; libc harness logging remains separate.
 config=(o/'config.h').read_bytes();formatter(s,o);(o/'config.h').write_bytes(config)
 sources=['card.c','host103.c','printf103.c','ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']
 write('product-output103.h','#include <stdio.h>\nint diag_printf(const char *,...);\n#define printf diag_printf\n')
 for i,n in enumerate(sources):
  if n in ['card.c','host103.c','printf103.c']:continue
  wrapper='linked103-'+n.replace('/','-')
  write(wrapper,'#include "product-output103.h"\n#include "'+n+'"\n');sources[i]=wrapper
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-fno-builtin','-ffunction-sections','-fdata-sections','-I.','-DGBC_SAVE_G12','-DGBC_DUMP_G12',*sources,'-Wl,--gc-sections','-o','host.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 assert not r.returncode,(o/'compile.log').read_text(errors='replace')[-6000:]
 cases=[x['case'] for x in json.loads((source/'result.json').read_bytes())['cases']];results=[]
 if a.uart_stall:cases=[x for x in cases if x[1]!=0]
 for i,case in enumerate(cases):
  log=o/f'case-{i}.log';args=list(map(str,case))+[str(o/n) for n in ['fixture.nes','diag.packed','diag.raw','base.packed','base.raw','menu.bin']]
  with log.open('wb') as f:r=subprocess.run([str(o/'host.exe'),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  text=log.read_text(errors='replace');assert not r.returncode and 'PASS103' in text,text[-3000:]
  results.append(dict(case=case,exit=r.returncode,log_sha256=sha(log),last=text.strip().splitlines()[-1]))
 write('result.json',json.dumps(dict(cases=results,inputs=inputs,geometry96=a.geometry96,uart_stall=a.uart_stall,physical=False,installable=False),indent=2)+'\n');print('PASS103 main/actual observer/formatter/UART cases='+str(len(results)))
if __name__=='__main__':main()
