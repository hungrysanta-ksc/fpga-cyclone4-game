# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,re,runpy,collections
from audit_fpga_signoff import parse_reports
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def number(pattern,text):
 m=re.search(pattern,text);assert m,pattern
 return int(m[1].replace(',',''))
def verify(root,repo):
 build=root/'build';rtl=root/'rtl';resource=root/'resource'
 bm=json.loads((build/'result.json').read_text());rm=json.loads((rtl/'result.json').read_text());fm=json.loads((resource/'result.json').read_text())
 assert bm['driver_sha256']==sha(repo/'tools/build_nes_h1_board.py')
 assert bm['base_builder_sha256']==sha(repo/'tools/build_nes_h1_pattern.py')
 assert bm['derived_builder_sha256']==sha(build/'derived-builder.py')
 rom=(build/'build/nes-h1-board-034.sfc').read_bytes()
 assert sha(build/'build/nes-h1-board-034.sfc')==bm['rom_sha256']
 compact=bytes(int(x,16) for x in (build/'build/h1-program.hex').read_text().split())
 def read(i):
  bank,off=divmod(i,32768)
  if bank:return compact[0x4000+off] if off<0x2000 else 255
  if off<0x3200:return compact[off]
  return compact[0x3fc0+(off&63)] if off>=0x7fc0 else 255
 assert len(compact)==24576 and bytes(read(i) for i in range(65536))==rom
 assert rm['driver_sha256']==sha(repo/'tools/nes_h1_board.py') and rm['passed']
 assert rm['phases']=={'vlib':0,'compile':0,'board':0}
 for name,digest in rm['sources'].items():assert sha(repo/name)==sha(rtl/Path(name).name)==digest,name
 for name,digest in rm['inputs'].items():assert sha(rtl/name)==sha(build/'build'/name)==digest,name
 log=(rtl/'board.log').read_text(errors='replace')
 assert 'PASS NES H1 BOARD checks=6 rombytes=65536 payloadbytes=8192' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 rows=[list(map(int,s.split())) for s in (rtl/'board-bytes.tsv').read_text().splitlines()]
 assert bytes(v for kind,addr,v in rows if kind==1)==rom
 payload=bytes(v for kind,addr,v in rows if kind==2)
 pattern=bytes(int(x,16) for x in (build/'build/h1-pattern.hex').read_text().split())
 assert payload==pattern+pattern[:2048] and payload==(build/'board-payload.bin').read_bytes()
 emulation={}
 for ep in (1,2):
  out=root/('epoch'+str(ep));meta=json.loads((out/'result.json').read_text());capture=json.loads((out/'capture/capture.json').read_text())
  assert meta['epoch']==ep and meta['driver_sha256']==sha(repo/'tools/run_nes_h1_board_client.py')
  assert meta['derived_runner_sha256']==sha(out/'runner.py') and meta['derived_observer_sha256']==sha(out/'observer.lua')
  assert meta['board_payload_sha256']==sha(build/'board-payload.bin')
  assert capture['exit_code']==0 and capture['rom_sha256']==bm['rom_sha256']
  assert capture['observer_sha256']==sha(out/'observer.lua') and capture['runner_sha256']==sha(out/'runner.py')
  assert (out/'rtl-bytes.bin').read_bytes()==pattern*2+pattern[:2048]
  assert capture['rtl_bytes_sha256']==sha(out/'rtl-bytes.bin')
  module=runpy.run_path(str(out/'runner.py'),run_name='board_audit')
  emulation[str(ep)]=module['audit'](build/'build',out/'rtl-bytes.bin',out/'capture','normal')
  trace=[row.split() for row in (out/'capture/trace.tsv').read_text().splitlines()]
  assert [int(row[2]) for row in trace if row[:2]==['R','24587']]==[ep]*6
  assert [int(row[2]) for row in trace if row[:2]==['W','24578']]==[ep]*6
 assert fm['driver_sha256']==sha(repo/'tools/nes_h1_board_resource.py') and fm['phases']=={'map':0,'fit':0,'sta':0}
 for name,digest in fm['sources'].items():assert sha(repo/name)==sha(resource/Path(name).name)==digest,name
 for name,digest in fm['inputs'].items():assert sha(resource/name)==sha(build/'build'/name)==digest
 assert fm['pin_source_sha256']==sha(repo/'src/fpga/pin.qsf') and fm['physical_pin_assignments']==135
 qsf=(resource/'board.qsf').read_text();sdc=(resource/'board.sdc').read_text()
 assert 'VIRTUAL_PIN' not in qsf and not re.search(r'^set_(?:false_path|multicycle_path|clock_groups)',sdc,re.M)
 original_pins={s for s in (repo/'src/fpga/pin.qsf').read_text().splitlines() if s.startswith('set_location_assignment')}
 pins={s for s in qsf.splitlines() if s.startswith('set_location_assignment')}
 assert len(pins)==135 and pins<=original_pins
 report=(resource/'output_files/board.fit.rpt').read_text(encoding='latin-1')
 fit=(resource/'output_files/board.fit.summary').read_text(encoding='latin-1')
 sta=(resource/'output_files/board.sta.rpt').read_text(encoding='latin-1')
 summary=(resource/'output_files/board.sta.summary').read_text(encoding='latin-1')
 assert 'Fitter Status : Successful' in fit and 'fxpak_nes_h1_top' in fit
 metrics={'LE':number(r'Total logic elements\s*:\s*([\d,]+)',fit),'LAB':number(r'Total LABs:\s*partially or completely used\s*;\s*([\d,]+)',report),'M9K':number(r'; M9Ks\s*;\s*([\d,]+)',report),'memory_bits':number(r'Total memory bits\s*:\s*([\d,]+)',fit),'physical_pins':number(r'Total pins\s*:\s*([\d,]+)',fit),'virtual_pins':number(r'Total virtual pins\s*:\s*([\d,]+)',fit),'PLLs':number(r'Total PLLs\s*:\s*([\d,]+)',fit)}
 assert metrics['memory_bits']==319488 and metrics['M9K']==44 and metrics['physical_pins']==135 and metrics['virtual_pins']==0 and metrics['PLLs']==1
 timing=parse_reports(summary,sta,fit,report)
 assert timing['constrained_slack_pass'] and not timing['design_signoff']
 assert timing['check_timing_raw_summary']['Unconstrained Input Ports']=={'setup':38,'hold':38}
 assert timing['check_timing_raw_summary']['Unconstrained Output Ports']=={'setup':11,'hold':11}
 host=json.loads((root/'host/result.json').read_text())
 assert host['passed'] and host['cases']==7 and 'PASS H1 SESSION cases=7' in (root/'host/build.log').read_text(encoding='utf-8-sig',errors='replace')
 for name,digest in host['sources'].items():assert sha(repo/name)==sha(root/'host'/Path(name).name)==digest
 warnings={}
 for phase in ('map','fit','sta'):
  text=(resource/(phase+'.log')).read_text(encoding='latin-1')
  assert not re.search(r'(?m)^\s*Error \(\d+\)',text)
  warnings[phase]=dict(collections.Counter(re.findall(r'(?m)^\s*(?:Critical )?Warning \((\d+)\)',text)))
 return {'candidate':'NES-H1-BOARD-034','bounded_tests_passed':True,'hardware_eligible':False,'rtl_cases':6,'rtl_rom_bytes':65536,'rtl_payload_bytes':8192,'emulator_epochs':emulation,'emulator_exact_pixels':856576,'host_C_cases':7,'resource':metrics,'timing':timing,'warning_codes':warnings,'limits':'Internal STA only.38input/11output ports unconstrained. MCU callback code host-tested but not STM32-bound or full firmware built. No bitstream deployment or physical execution. No NES game core.','verifier_sha256':sha(__file__)}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 result=verify(a.root,Path(__file__).resolve().parents[1]);a.out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'resource':result['resource'],'minimum_slack_ns':result['timing']['minimum_slack_ns'],'hardware_eligible':False,'warning_codes':result['warning_codes']},indent=2))
