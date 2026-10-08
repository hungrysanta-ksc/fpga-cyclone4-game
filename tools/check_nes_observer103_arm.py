# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,re,subprocess
from nes_spi_boot import ROOT,sha
from test_nes_menu098 import definition
from check_nes_quiesce102_arm import interpret

def main():
 p=argparse.ArgumentParser()
 for n in ['arm','evidence102','unit','main','objdump','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();s=a.arm/'src';e=a.evidence102
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/quiesce102-verification.json').read_bytes())['manifest_sha256']
 prep=json.loads((a.arm/'preparation103.json').read_bytes());retained={}
 for n,h in prep['copied'].items():
  if n in prep['changed']:assert sha(a.arm/n)==prep['changed'][n]
  else:assert sha(a.arm/n)==h,n;retained[n]=h
 assert set(prep['changed'])=={'src/nes_diag_platform.c','src/stm32f4xx/uart.c','src/VERSION'}
 # Match actual tested production sources, not just a model with similar behavior.
 for host,prefix in [(a.unit,'production-'),(a.main,'production103-')]:
  for n in ['nes_diag_platform.c','stm32f4xx/uart.c','printf.c']:
   assert (host/(prefix+n.replace('/','-'))).read_text()==(s/n).read_text(),n
 for n in ['main098.inc','load098.inc']:
  assert (a.main/n).read_bytes()==(e/'main02'/n).read_bytes()
 assert definition((s/'nes_diag_platform.c').read_text(),'nes_diag_spi_quiesce102')==definition((e/'arm01/src/nes_diag_platform.c').read_text(),'nes_diag_spi_quiesce102')
 elf=s/'obj-nes-100/sd2snes.elf';fw=s/'obj-nes-100/firmware.stm';d={}
 for n in ['nes_diag_observe','nes_diag_spi_quiesce102','nes_diag_blocked','nes_diag_fail','nes_return_fail','nes_return_failed','uart_putc','uart_flush','printf']:
  b=subprocess.check_output([str(a.objdump),'-d','--disassemble='+n,str(elf)]);(a.arm/(n+'-checked103.txt')).write_bytes(b);d[n]=b.decode();assert '<'+n+'>:' in d[n]
 # On active + shared fault, the first branch falls through directly to reset
 # and tail-calls quiesce; its alternate target starts normal LED/UART work.
 obs=d['nes_diag_observe'];cut=obs.index('<nes_return_failed>');tail=obs[cut:]
 branch=re.search(r'\bcbz\s+r0, ([0-9a-f]+)',tail);assert branch
 normal=int(branch[1],16);qline=next(x for x in tail.splitlines() if '<nes_diag_spi_quiesce102>' in x)
 qaddr=int(qline.strip().split(':')[0],16);assert qaddr<normal and re.search(r'\bb\.w\s',qline)
 segment=tail[:tail.index(qline)+len(qline)]
 assert re.findall(r'<([a-zA-Z_][a-zA-Z_0-9]*)>',segment)==['nes_return_failed','snes_reset','nes_diag_spi_quiesce102']
 assert 'dsb' in segment and 'isb' in segment
 for n in ['uart_putc','uart_flush']:
  t=d[n];cut=t.index('<nes_return_failed>');end=t.index('<nes_diag_wait_start>');part=t[cut:end]
  b=re.search(r'\bcbz\s+r0, ([0-9a-f]+)',part);assert b
  target=int(b[1],16);pop=next(x for x in part.splitlines() if re.search(r'\bpop\s.*pc',x));assert int(pop.strip().split(':')[0],16)<target
  assert '<nes_diag_active>' in t[:cut] and '<nes_diag_wait_step>' in t
 assert '<nes_diag_fail>' in d['nes_return_fail'] and '<nes_diag_observe>' in d['nes_diag_fail']
 assert '<nes_diag_sd_failed>' in d['nes_return_failed']
 traces=[interpret(d['nes_diag_spi_quiesce102'],x*0x1020304) for x in range(16)]
 (a.arm/'mmio-arm103.json').write_text(json.dumps(traces,indent=2)+'\n')
 result=dict(firmware_bytes=fw.stat().st_size,firmware_sha256=sha(fw),elf_sha256=sha(elf),retained_inputs=len(retained),changed=prep['changed'],arm_mmio_cases=16,shared_fault_observer_precedes_waiting_output=True,physical_latency_proven=False,whole_timer_cic_integrated=False,physical=False,installable=False)
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('PASS103 ARM fault branch bypasses LED/UART; UART suppression branches and16 MMIO interpretations')
if __name__=='__main__':main()
