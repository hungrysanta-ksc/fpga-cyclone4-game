# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_spi_boot import ROOT,sha
from nes_menu098 import once
from test_nes_menu098 import definition

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence103','arm','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--geometry96',action='store_true');p.add_argument('--units',action='store_true')
 p.add_argument('--timer-stall',choices=['ticks','frozen'])
 p.add_argument('--mutation',choices=['baseline','timer-bound','timer-cleanup','card-state','reset-invert','cic-threshold'])
 a=p.parse_args();e=a.evidence103.resolve();s=a.arm.resolve()/'src';o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/observer103-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];source=e/('fat32-96-02' if a.geometry96 else 'main04');inputs={}
 def write(n,t):(o/n).write_text(t,encoding='utf-8',newline='\n')
 for f in source.rglob('*'):
  if f.is_file() and f.suffix in ['.c','.h','.inc','.packed','.raw','.bin','.nes']:
   key=f.relative_to(e).as_posix();assert sha(f)==pins[key];inputs[key]=sha(f);dst=o/f.relative_to(source);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
 shutil.copy2(__file__,o/'executed-test104.py')
 for n in ['peripherals104_model.inc','peripherals104_cases.inc']:shutil.copy2(ROOT/'tests/nes-functional'/n,o/n)
 for n in ['stm32f4xx/timer.c','stm32f4xx/led.c','stm32f4xx/sdnative.c','cic.c','cic.h','snes.c','cfg.c','stm32f4xx/timer.h']:
  shutil.copy2(s/n,o/('production104-'+n.replace('/','-')))
 timer=(s/'stm32f4xx/timer.c').read_text();led=(s/'stm32f4xx/led.c').read_text();cic=(s/'cic.c').read_text();reset=(s/'snes.c').read_text()
 t='\n'.join(definition(timer,n) for n in ['nes_return_delay','delay_us','delay_ms'])
 if a.mutation=='timer-bound':t=once(t,'if(!nes_diag_wait_step(&wait))','if(false)')
 if a.mutation=='timer-cleanup':t=once(t,'BITBAND(TIM2->SR,TIM_SR_UIF_Pos)=0;TIM2->CR1=0;','/* no cleanup */')
 write('timer104.inc',t)
 lednames=['rdybright','readbright','writebright','rdyled','readled','writeled','led_pwm','led_std','led_set_brightness','led_error']
 table=led[led.index('static uint16_t led_bright'):led.index('int led_rdyledstate')]
 write('led104.inc',table+'\n'.join(definition(led,n) for n in lednames))
 text='\n'.join(definition(cic,n) for n in ['cic_init','cic_videomode','cic_d4','cic_pair','get_cic_state'])
 text=once(text,'void cic_pair(int init_vmode, int init_d4) {','void cic_pair(int init_vmode, int init_d4) {\n pair098++;')
 if a.mutation=='cic-threshold':text=once(text,'togglecount > CIC_TOGGLE_THRESH_PAIR','togglecount >= CIC_TOGGLE_THRESH_PAIR')
 write('cic104.inc',definition((s/'cfg.c').read_text(),'cfg_is_pair_mode_allowed')+text)
 text=definition(reset,'get_snes_reset')
 if a.mutation=='reset-invert':text=once(text,'return !BITBAND','return BITBAND')
 write('reset104.inc',text)
 systick=definition(timer.replace('__attribute__((weak,noinline)) ',''),'SysTick_Hook')+definition(timer,'SysTick_Handler')
 write('systick104.inc',systick)
 h=(e/'arm01/src/obj-nes-100/autoconf.h').read_text();c=(s/'include/arm/ST/STM32F4/stm32f401xc.h').read_text()
 macros='\n'.join(x for x in h.splitlines() if re.match(r'#define (?:CONFIG_CPU_FREQUENCY\s|SNES_CIC_|SNES_RESET_|LED_(?:READY|READ|WRITE)_(?:REG|BIT)|GPIO_MODE_|GPIO_OPENDRAIN|GPIO_SEL_AF)',x))
 macros+='\n'+'\n'.join(re.findall(r'^#define (?:TIM_SR_UIF|TIM_CR1_(?:URS|DIR|CEN))(?:_Pos|_Msk)?\s[^\n]*',c,re.M))
 write('peripheral-registers104.h',macros+'\n')
 mh=(o/'mcu_loader_platform.h').read_text();mh=once(mh,'uint32_t MODER,ODR,IDR,OTYPER,BSRR;','uint32_t MODER,ODR,IDR,OTYPER,BSRR,AFR[2];').replace('int get_snes_reset(void);','uint8_t get_snes_reset(void);');write('mcu_loader_platform.h',mh)
 plat=(o/'platform.c').read_text();plat=once(plat,definition(plat,'get_snes_reset'),'');plat=once(plat,definition(plat,'delay_ms'),'')
 plat=once(plat,'void delay_us(unsigned v)','static void wire_delay_us104(unsigned v)')
 plat=once(plat,'tick_t getticks(void){return clock096();}','extern volatile tick_t ticks;\ntick_t getticks(void){return ticks;}')
 write('platform.c',plat)
 pre=(o/'host098-prefix.inc').read_text();pre=once(pre,'uint32_t clock096(void){','static void service104(void);\nuint32_t clock096(void){')
 pre=once(pre,'return clock096();','service104();return ticks;');write('host098-prefix.inc',pre)
 card=(o/'card.c').read_text();sd=(s/'stm32f4xx/sdnative.c').read_text()
 if a.mutation=='baseline':sd=(e/'arm01/src/stm32f4xx/sdnative.c').read_text()
 changed=definition(sd,'sdn_changed')
 if a.mutation=='card-state':changed=once(changed,'disk_state = DISK_CHANGED;','/* omitted state update */')
 write('sdn-changed104.inc',changed)
 card+='\nvolatile int sd_changed;\nunsigned card_detect104(void){return card;}\n#define SDCARD_DETECT card\nint diag_printf(const char *,...);\n#define printf diag_printf\n#include "sdn-changed104.inc"\n'
 write('card.c',card)
 host=(o/'host103.c').read_text()
 for text in ['MODEL_VOID(led_set_brightness,(uint8_t v))']+[f'static void {n}(unsigned v){{(void)v;}} /* LED GPIO effects remain modeled. */' for n in ['rdyled','readled','writeled']]:host=once(host,text,'')
 begin=host.index('void cic_init(int allow)');end=host.index('void actual_snes_reset102',begin);host=host[:begin]+host[end:]
 host=once(host,'reset_held=v;actual_snes_reset102(v);','reset_held=v;actual_snes_reset102(v);if(v)mock_a.IDR&=~1u;else mock_a.IDR|=1u;')
 host=once(host,'#include "lower100.inc"','#include "peripherals104_model.inc"\n#include "lower100.inc"')
 obs=(o/'observer-main103.inc').read_text()
 obs=once(obs,'int led_pwmstate,led_rdyledstate,led_readledstate,led_writeledstate;','')
 for n in ['led_std','led_pwm']:obs=once(obs,definition(obs,n),'')
 obs=once(obs,' uart_reads103++;',' uart_preempt104();uart_reads103++;');write('observer-main103.inc',obs)
 host=once(host,'#undef printf\nint main','#include "peripherals104_cases.inc"\n#undef printf\nint main')
 host=once(host,'initialize(NONE,1);mock_a.IDR=32;setup_rtc099(baseline098);','initialize(NONE,1);mock_a.IDR=32;setup_rtc099(baseline098);\n if(scenario098==100){run_units104(baseline098);return 0;}')
 host=once(host,'native_ns096=ns=0;poll096=0;measured096=1;','native_ns096=ns=0;ticks=0;next_tick104=10000000ull;poll096=0;measured096=1;')
 if a.timer_stall:
  host=once(host,'polls099=0;begin_lower100(baseline098);init102();','polls099=0;begin_lower100(baseline098);init102();timer_stall104=1;tick_freeze104='+str(int(a.timer_stall=='frozen'))+';')
  host=once(host,'if(baseline098){\n  assert(terminal102', 'if(timer_stall104){\n  assert(!ok&&blocked098&&nes_return_failed()&&!irq&&reset_held&&!release097);\n  assert(nes_diag_status()->error==NES_DIAG_TIMER&&!TIM2->CR1&&!timer_alias104);\n  check_quiesce102();assert_quiet100();\n }else if(baseline098){\n  assert(terminal102')
 host=host.replace('PASS103','PASS104');write('host104.c',host)
 sources=['card.c','host104.c','printf103.c']+['linked103-'+n.replace('/','-') for n in ['ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']]
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-fno-builtin','-ffunction-sections','-fdata-sections','-I.','-DGBC_SAVE_G12','-DGBC_DUMP_G12',*sources,'-Wl,--gc-sections','-o','host.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 assert not r.returncode,(o/'compile.log').read_text(errors='replace')[-7000:]
 cases=[[100,i] for i in range(60)] if a.units else [x['case'] for x in json.loads((source/'result.json').read_bytes())['cases']]
 if not a.units and not a.geometry96:cases += [[2,0],[3,0]]
 if a.timer_stall:cases=[[0,0]]
 if a.mutation:cases=[[100,{'baseline':20,'timer-bound':1,'timer-cleanup':0,'card-state':20,'reset-invert':10,'cic-threshold':15}[a.mutation]]]
 results=[]
 for i,case in enumerate(cases):
  log=o/f'case-{i}.log';args=list(map(str,case))+[str(o/n) for n in ['fixture.nes','diag.packed','diag.raw','base.packed','base.raw','menu.bin']]
  with log.open('wb') as f:r=subprocess.run([str(o/'host.exe'),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  text=log.read_text(errors='replace')
  if a.mutation:assert r.returncode and 'Assertion' in text,text[-2000:]
  else:assert not r.returncode and 'PASS104' in text,text[-2500:]
  results.append(dict(case=case,exit=r.returncode,log_sha256=sha(log),last=text.strip().splitlines()[-1]))
 write('result.json',json.dumps(dict(cases=results,inputs=inputs,geometry96=a.geometry96,units=a.units,timer_stall=a.timer_stall,mutation=a.mutation,physical=False,installable=False),indent=2)+'\n')
 print('PASS104 actual timer/SysTick/LED/CIC/reset cases='+str(len(results)))
if __name__=='__main__':main()
