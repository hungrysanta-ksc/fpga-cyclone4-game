# SPDX-License-Identifier: MIT
from pathlib import Path
import ast,json,re,subprocess,zipfile
from nes_h1_spi import sha
from nes_h1_fault import source,session,boundary
from nes_h1_fault_resource import decode_rle
from manage_nes_h1_fault_sd import payload,EXPECTED,FIRMWARE,FPGA,BASELINE_FW
ROOT=Path(__file__).resolve().parents[1]
def main():
 r=ROOT;raw=r/'analysis/local-h1-fault-039';count=0
 for group,entries in json.loads((r/'analysis/h1-runtime-artifacts.json').read_text()).items():
  if group not in ('sources','status_files','evidence'):continue
  for e in entries:
   p=(raw/'baseline-status' if group=='status_files' else r)/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];count+=1
 assert count==175
 c44=json.loads((r/'source-manifest.json').read_text())['files']
 for e in c44:assert sha(r/e['path'])==e['sha256'],e['path']
 assert (raw/'arm/nes_h1_stm32.c').read_text()==source()
 for name in ('main.c','filetypes.c','nes_h1_session.h','nes_h1_stm32.h','Makefile'):
  assert sha(raw/'arm'/name)==sha(r/'analysis/local-h1-firmware-035/arm-final/src'/name),name
 assert sha(r/'analysis/local-h1-runtime-038/arm/firmware.stm')==BASELINE_FW
 assert sha(raw/'arm/firmware.stm')==EXPECTED[FIRMWARE]
 assert b'candidate=NES-H1-FAULT-039' in (raw/'arm/firmware.stm').read_bytes()
 assert b'/sd2snes/nes-h1-last-039.txt' in (raw/'arm/firmware.stm').read_bytes()
 log=(raw/'arm-build.log').read_text(errors='replace');assert not re.search(r'\b(?:warning|error):',log) and 'PASS: experimental H1 firmware '+EXPECTED[FIRMWARE] in log
 host=json.loads((raw/'host-01/result.json').read_text());assert len(host['cases'])==15
 rtl=json.loads((raw/'rtl/result.json').read_text());assert rtl['passed'] and rtl['samples']==448 and rtl['verified_bits']==200
 assert 'PASS C SPI WAVE samples=448 verified=200 rows=1880' in (raw/'rtl/wave.log').read_text()
 assert not re.search(r'\*\* (?:Fatal|Error):',(raw/'rtl/wave.log').read_text())
 assert sha(raw/'host-01/waveform.txt')==sha(raw/'rtl/waveform.txt')
 assert sha(raw/'rtl/nes_h1_board_bus.sv')==sha(raw/'resource/nes_h1_board_bus.sv')

 assert (raw/'arm/nes_h1_session.c').read_text()==session()
 assert (raw/'rtl/nes_h1_board_bus.sv').read_text()==boundary()
 log=(raw/'rtl/board.log').read_text();assert 'PASS NES H1 BOARD checks=9 rombytes=65536 payloadbytes=8192' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 fit=raw/'resource';m=json.loads((fit/'result.json').read_text());assert m['phases']==dict(map=0,fit=0,sta=0,asm=0)
 assert sha(fit/'nes_h1_board_bus.sv')==m['compiled_boundary_sha256']
 assert sha(fit/'fpga_nh1.bi3')==EXPECTED[FPGA]==m['bi3_sha256']
 assert decode_rle((fit/'fpga_nh1.bi3').read_bytes())==(fit/'output_files/board.rbf').read_bytes()
 decoder=json.loads((raw/'decoder/result.json').read_text());assert decoder['passed'] and decoder['bytes']==m['rbf_bytes'] and decoder['bi3_sha256']==EXPECTED[FPGA]
 for n in ('h1-pattern.hex','h1-program.hex','board.sdc'):
  assert sha(fit/n)==sha(r/'analysis/local-h1-spi-036/resource'/n),n
 oldq=(r/'analysis/local-h1-spi-036/resource/board.qsf').read_text();newq=(fit/'board.qsf').read_text()
 assert sorted(x for x in oldq.splitlines() if x.startswith('set_location_assignment'))==sorted(x for x in newq.splitlines() if x.startswith('set_location_assignment'))
 slacks=[float(v) for v in re.findall(r'Slack\s*:\s*([-\d.]+)',(fit/'output_files/board.sta.summary').read_text())];assert slacks and min(slacks)>0
 hostc=(raw/'host-01/binding.c').read_text().replace('h1_read_miso()','((GPIOB->IDR>>4)&1u)');assert hostc==source()
 assert json.loads((raw/'install-tests/result.json').read_text())['passed']==8
 pkg=raw/'NES-H1-FAULT-039';payload(pkg)
 assert sha(pkg/'manage_nes_h1_fault_sd.py')==sha(r/'tools/manage_nes_h1_fault_sd.py')
 assert sha(pkg/'READ-ME.ko.md')==sha(r/'docs/nes-h1-fault-test.ko.md')
 result=json.loads((r/'analysis/h1-fault-verification.json').read_text());assert sha(pkg.with_suffix('.zip'))==result['zip_sha256']
 with zipfile.ZipFile(pkg.with_suffix('.zip')) as z:
  files={f.relative_to(pkg).as_posix():f.read_bytes() for f in pkg.rglob('*') if f.is_file()};assert set(files)==set(z.namelist())
  for n,b in files.items():assert z.read(n)==b
 before=json.loads((raw/'baseline-status/cores/registry.json').read_text());after=json.loads((r/'cores/registry.json').read_text())
 assert [x for x in before['cores'] if x['id']!='nes']==[x for x in after['cores'] if x['id']!='nes']
 before=json.loads((raw/'baseline-status/analysis/hardware-readiness.json').read_text());after=json.loads((r/'analysis/hardware-readiness.json').read_text())
 assert {k:v for k,v in before.items() if k!='H1'}=={k:v for k,v in after.items() if k!='H1'}
 assert after['H1']['last_hardware_observation']['hardware_executed'] and not after['H1']['last_hardware_observation']['hardware_verified']
 assert json.loads((r/'docs/nes-development-plan.json').read_text())['hardware_tracks']['H1']==after['H1']
 def git(*args,cwd=r,data=None,success=(0,)):
  cp=subprocess.run(['git','-c','safe.directory='+cwd.as_posix(),*args],cwd=cwd,input=data,capture_output=True);assert cp.returncode in success,cp.stderr.decode(errors='replace');return cp.stdout
 assert not git('diff','--cached','--name-only').strip()
 assert not git('diff','HEAD','--','src/fpga','src/firmware-overlay','src/renderer','cores/gbc','release','source-manifest.json').strip()
 git('diff','--check')
 names=json.loads((raw/'public-files.json').read_text())
 for n in names:
  if n.endswith('.py'):ast.parse((r/n).read_text())
  if n.endswith('.md'):
   for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)',(r/n).read_text()):
    if '://' not in link:assert ((r/n).parent/link).exists(),link
 assert not git('check-ignore','-z','--stdin',data=('\0'.join(names)+'\0').encode(),success=(0,1))
 files=[f.relative_to(r).as_posix() for f in raw.rglob('*') if f.is_file()]
 ignored=git('check-ignore','-z','--stdin',data=('\0'.join(files)+'\0').encode()).decode().strip('\0').split('\0');assert set(files)==set(ignored)
 upstream=r.parent/'nes-upstream-mister';assert git('rev-parse','HEAD',cwd=upstream).decode().strip()=='49a0a662e244469ca77b2155746a066df704ffae';assert not git('status','--porcelain',cwd=upstream).strip()
 manifest=r/'analysis/h1-fault-artifacts.json';total=0
 if manifest.exists():
  m=json.loads(manifest.read_text())
  for group in ('sources','status_files','evidence'):
   for e in m[group]:
    p=r/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];total+=1
 print(json.dumps({'previous038_entries':count,'GBC_hashes':len(c44),'host_cases':15,'SPI_waveform':'PASS448samples200bits','board_cases':9,'physical_fit_internal_STA_ASM':'PASS','MCU_decoder':'PASS215453bytes','installer_cases':8,'package_integrity':'PASS','protected_GBC_nonNES_H0':'unchanged','staged_files':0,'git_diff_check':'PASS','upstream_pin_clean':'PASS','public_allowlist':'PASS','raw_ignored':len(files),'manifest_entries':total},indent=2))
if __name__=='__main__':main()
