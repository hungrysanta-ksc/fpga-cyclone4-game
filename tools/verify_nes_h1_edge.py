# SPDX-License-Identifier: MIT
from pathlib import Path
import ast,json,re,subprocess,zipfile
from nes_h1_spi import sha
from nes_h1_edge import frontend,boundary,transport,pattern,source,session
from nes_h1_fault_resource import decode_rle
from manage_nes_h1_edge_sd import payload,EXPECTED,FPGA,FIRMWARE,BASELINE_FW
ROOT=Path(__file__).resolve().parents[1]
def main():
 r=ROOT;raw=r/'analysis/local-h1-edge-041';old_count=0
 for group in ('sources','status_files','evidence'):
  for e in json.loads((r/'analysis/h1-release-artifacts.json').read_text())[group]:
   p=(raw/'baseline-status' if group=='status_files' else r)/e['path']
   assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];old_count+=1
 assert old_count==228
 c44=json.loads((r/'source-manifest.json').read_text())['files']
 for e in c44:assert sha(r/e['path'])==e['sha256'],e['path']
 assert sha(r/'analysis/local-h1-fault-039/arm/firmware.stm')==BASELINE_FW
 rtl=raw/'rtl';fit=raw/'resource'
 for d in (rtl,fit):
  assert (d/'nes_snes_frontend.sv').read_text()==frontend()
  assert (d/'nes_h1_board_bus.sv').read_text()==boundary()
  assert (d/'nes_transport.sv').read_text()==transport()
  assert (d/'nes_h1_pattern.sv').read_text()==pattern()
 assert sha(rtl/'nes_snes_frontend.sv')==sha(fit/'nes_snes_frontend.sv')
 assert sha(rtl/'nes_h1_board_bus.sv')==sha(fit/'nes_h1_board_bus.sv')
 assert (raw/'arm/nes_h1_stm32.c').read_text()==source() and (raw/'arm/nes_h1_session.c').read_text()==session()
 assert sha(raw/'arm/firmware.stm')==EXPECTED[FIRMWARE]
 assert b'candidate=NES-H1-EDGE-041' in (raw/'arm/firmware.stm').read_bytes()
 assert b'/sd2snes/nes-h1-last-041.txt' in (raw/'arm/firmware.stm').read_bytes()
 assert not re.search(r'\b(?:warning|error):',(raw/'arm-build.log').read_text(errors='replace'))
 assert len(json.loads((raw/'host/result.json').read_text())['cases'])==15
 assert (raw/'host/binding.c').read_text().replace('h1_read_miso()','((GPIOB->IDR>>4)&1u)')==source()
 m=json.loads((rtl/'result.json').read_text());assert m['passed'] and m['samples']==704 and m['verified_bits']==328
 assert m['release']['normal_cases']==156 and m['release']['real_abort_cases']==84 and m['release']['legacy_false_abort_cases']==120
 assert sha(rtl/'waveform.txt')==sha(raw/'host/waveform.txt')==m['waveform_sha256']
 for file,marker in [('edge.log','PASS RELEASE good=156 abort=84 legacy_false_abort=120'),('board.log','PASS NES H1 BOARD checks=9 rombytes=65536 payloadbytes=8192'),('wave.log','PASS C SPI WAVE samples=704 verified=328 rows=2952')]:
  log=(rtl/file).read_text();assert marker in log and not re.search(r'\*\* (?:Fatal|Error):',log),file
 assert 'PASS CAUSAL COUNTERS low=10 previous_low=12 previous_high=8 saturation=255' in (rtl/'edge.log').read_text()
 assert m['release']['040_behavior_equal_each_edge'] and m['release']['counter_calibration_and_saturation']
 fit_result=json.loads((fit/'result.json').read_text());assert fit_result['phases']==dict(map=0,fit=0,sta=0,asm=0)
 assert fit_result['compiled_frontend_sha256']==m['frontend_sha256']==sha(fit/'nes_snes_frontend.sv')
 assert sha(fit/'fpga_nh1.bi3')==EXPECTED[FPGA]==fit_result['bi3_sha256']
 assert decode_rle((fit/'fpga_nh1.bi3').read_bytes())==(fit/'output_files/board.rbf').read_bytes()
 decoder=json.loads((raw/'decoder/result.json').read_text());assert decoder['passed'] and decoder['bytes']==218719 and decoder['bi3_sha256']==EXPECTED[FPGA]
 for n in ('h1-pattern.hex','h1-program.hex','board.sdc','board.qsf'):
  assert sha(fit/n)==sha(r/'analysis/local-h1-fault-039/resource'/n),n
 slacks=[float(v) for v in re.findall(r'Slack\s*:\s*([-\d.]+)',(fit/'output_files/board.sta.summary').read_text())];assert min(slacks)>0
 assert json.loads((raw/'install-tests/result.json').read_text())['passed']==8
 package=raw/'NES-H1-EDGE-041';payload(package)
 assert sha(package/'manage_nes_h1_edge_sd.py')==sha(r/'tools/manage_nes_h1_edge_sd.py')
 assert sha(package/'READ-ME.ko.md')==sha(r/'docs/nes-h1-edge-test.ko.md')
 assert sha(package/'reference-034.png')==sha(r/'analysis/local-h1-board-034/board-reference-contact.png')
 assert set(f.relative_to(package/'sd-overlay').as_posix() for f in (package/'sd-overlay').rglob('*') if f.is_file())=={FPGA,FIRMWARE}
 result=json.loads((r/'analysis/h1-edge-verification.json').read_text());assert sha(package.with_suffix('.zip'))==result['zip_sha256']
 with zipfile.ZipFile(package.with_suffix('.zip')) as z:
  files={f.relative_to(package).as_posix():f.read_bytes() for f in package.rglob('*') if f.is_file()};assert set(files)==set(z.namelist())
  for n,b in files.items():assert z.read(n)==b
 before=json.loads((raw/'baseline-status/cores/registry.json').read_text());after=json.loads((r/'cores/registry.json').read_text())
 assert [x for x in before['cores'] if x['id']!='nes']==[x for x in after['cores'] if x['id']!='nes']
 before=json.loads((raw/'baseline-status/analysis/hardware-readiness.json').read_text());after=json.loads((r/'analysis/hardware-readiness.json').read_text())
 assert {k:v for k,v in before.items() if k!='H1'}=={k:v for k,v in after.items() if k!='H1'}
 assert after['H1']['candidate']=='NES-H1-EDGE-041' and not after['H1']['hardware_executed']
 assert after['H1']['last_hardware_observation']['candidate']=='NES-H1-RELEASE-040'
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
 total=0;manifest=r/'analysis/h1-edge-artifacts.json'
 if manifest.exists():
  manifest_data=json.loads(manifest.read_text())
  for group in ('sources','status_files','evidence'):
   for e in manifest_data[group]:
    p=r/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];total+=1
 print(json.dumps({'previous040_entries':old_count,'GBC_hashes':len(c44),'normal_release_cases':156,'real_abort_cases':84,'legacy_false_abort_cases':120,'causal_snapshot_counter_calibration':True,'board_cases':9,'SPI_waveform':'704 samples / 328 consumed bits','physical_fit_internal_STA_ASM':'PASS','MCU_decoder_bytes':218719,'installer_cases':8,'package_integrity':'PASS','protected_GBC_nonNES_H0':'unchanged','staged_files':0,'git_diff_check':'PASS','upstream_pin_clean':'PASS','public_allowlist':'PASS','raw_ignored':len(files),'manifest_entries':total},indent=2))
if __name__=='__main__':main()
