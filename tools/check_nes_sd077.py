# SPDX-License-Identifier: MIT
"""Check source identity, ARM callers and077 host counterexamples."""
from pathlib import Path
import argparse,json,hashlib,re,subprocess,zlib
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--tests',type=Path,required=True);p.add_argument('--objdump',type=Path,required=True);a=p.parse_args();s=a.source;w=a.tests
 prep=json.loads((s/'preparation077.json').read_bytes());changed=[]
 for n,h in prep['baseline_inputs'].items():
  if Path(n).suffix in ['.c','.h','.S'] or Path(n).name in ['Makefile','VERSION']:
   if sha(s/n)!=h:changed.append(n)
 assert set(changed)=={'src/VERSION','src/stm32f4xx/sdnative.c'},changed
 tests=json.loads((w/'run-03/result.json').read_bytes());assert sha(s/'src/stm32f4xx/sdnative.c')==tests['candidate_sha256']
 assert all(tests['results'][n]['checks']==43 for n in ['baseline','candidate'])
 assert all(tests['results'][n]['exit']!=0 for n in ['no-end','short-tail'])
 baseline=(w/'run-03/baseline.log').read_text();candidate=(w/'run-03/candidate.log').read_text()
 assert 'after_status_end=6 candidate=0' in baseline and 'after_status_end=7 candidate=0' in baseline and 'corrupted_end_result=0' in baseline
 assert 'after_status_end=10 candidate=1' in candidate and 'corrupted_end_result=1' in candidate
 elf=s/'src/obj-nes-069/sd2snes.elf';fw=s/'src/obj-nes-069/firmware.stm';data=fw.read_bytes()
 assert data[:4]==b'STM3' and b'NES-SD077-CF68' in data and int.from_bytes(data[8:12],'little')==len(data)-512 and int.from_bytes(data[12:16],'little')==zlib.crc32(data[512:])
 calls={}
 for name in ['sdn_write','send_datablock','wait_busy','nes_diag_sd_error']:
  raw=subprocess.check_output([str(a.objdump),'-d','--disassemble='+name,str(elf)]);(w/(name+'-077.txt')).write_bytes(raw);calls[name]=re.findall(r'\b(?:bl(?:\.w)?|b\.w)\s+\w+\s+<([^>]+)>',raw.decode())
 assert 'send_datablock' in calls['sdn_write'] and 'nes_diag_active' in calls['send_datablock'] and 'nes_diag_sd_error' in calls['send_datablock'] and 'nes_diag_fail' in calls['nes_diag_sd_error']
 assert 'wait_busy' in calls['send_datablock'] and 'nes_diag_wait_step' in calls['wait_busy']
 log=(w/'arm-01.log').read_text(encoding='utf-8-sig');assert 'PASS069 manual ELF markers=3' in log and 'PASS069 CF68 compare and READY_before_GPIO' in log
 result=dict(candidate='NES-SD077-CF68',firmware_bytes=len(data),firmware_sha256=sha(fw),elf_sha256=sha(elf),changed_source076=changed,checks_each=43,mutations=2,calls=calls,physical=False,installable=False)
 (w/'check077.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
