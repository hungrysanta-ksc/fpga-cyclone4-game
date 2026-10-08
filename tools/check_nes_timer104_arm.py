# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,re,subprocess
from nes_spi_boot import ROOT,sha
from test_nes_menu098 import definition

def main():
 p=argparse.ArgumentParser()
 for n in ['arm','evidence103','host','objdump','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();s=a.arm/'src';e=a.evidence103
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/observer103-verification.json').read_bytes())['manifest_sha256']
 prep=json.loads((a.arm/'preparation104.json').read_bytes())
 assert set(prep['changed'])=={'src/stm32f4xx/sdnative.c','src/VERSION'}
 for n,h in prep['copied'].items():assert sha(a.arm/n)==prep['changed'].get(n,h),n
 names=['stm32f4xx/timer.c','stm32f4xx/led.c','stm32f4xx/sdnative.c','cic.c','cic.h','snes.c','cfg.c','stm32f4xx/timer.h']
 for n in names:assert (a.host/('production104-'+n.replace('/','-'))).read_bytes()==(s/n).read_bytes(),n
 for n in ['main098.inc','load098.inc','helpers098.inc','reliable098.inc']:
  assert (a.host/n).read_bytes()==(e/'main04'/n).read_bytes()
  assert not re.search(r'\bsleep_ms\s*\(', (a.host/n).read_text()),n
 assert (a.host/'sdn-changed104.inc').read_text()==definition((s/'stm32f4xx/sdnative.c').read_text(),'sdn_changed')
 elf=s/'obj-nes-100/sd2snes.elf';fw=s/'obj-nes-100/firmware.stm';d={}
 for n in ['sdn_changed','SysTick_Handler','SysTick_Hook','nes_return_delay','delay_us','delay_ms','get_cic_state','get_snes_reset','led_error','sleep_ms']:
  b=subprocess.check_output([str(a.objdump),'-d','--disassemble='+n,str(elf)]);(a.arm/(n+'-checked104.txt')).write_bytes(b);d[n]=b.decode();assert '<'+n+'>:' in d[n],n
 body=d['sdn_changed'];cut=body.index('<nes_diag_active>');tail=body[cut:]
 branch=re.search(r'\bcbnz\s+r0, ([0-9a-f]+)',tail);assert branch
 target=int(branch[1],16);line=next(x for x in tail.splitlines() if '<printf>' in x)
 assert int(line.strip().split(':')[0],16)<target
 after='\n'.join(x for x in tail.splitlines() if re.match(r'\s*[0-9a-f]+:',x) and int(x.strip().split(':')[0],16)>=target)
 assert not re.search(r'\bbl(?:x|\.w)?\s',after) and 'strb' in after and re.search(r'\bstr\s',after)
 assert '<sdn_changed>' in d['SysTick_Handler'] and '<printf>' not in d['SysTick_Handler']
 assert re.search(r'\bbx\s+lr',d['SysTick_Hook']) and not re.search(r'\bbl\s',d['SysTick_Hook'])
 for n in ['delay_us','delay_ms']:assert '<nes_diag_active>' in d[n] and '<nes_return_delay>' in d[n]
 assert '<nes_diag_wait_step>' in d['nes_return_delay'] and '<nes_return_fail>' in d['nes_return_delay']
 sym=subprocess.check_output([str(a.objdump),'-t',str(elf)]).decode();(a.arm/'symbols104.txt').write_text(sym)
 assert re.search(r'\bw\s+F\s+\.text\s+00000002 SysTick_Hook',sym)
 result=dict(firmware_bytes=fw.stat().st_size,firmware_sha256=sha(fw),elf_sha256=sha(elf),changed=prep['changed'],tested_production_sources={n:sha(s/n) for n in names},active_isr_skips_printf=True,card_state_updates_retained=True,systick_hook_weak_empty=True,extracted_menu_no_sleep_ms=True,arm_execution=False,physical=False,installable=False)
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('PASS104 ARM ISR branch skips printf and retains card-state writes; actual timer guard calls and weak empty hook')
if __name__=='__main__':main()
