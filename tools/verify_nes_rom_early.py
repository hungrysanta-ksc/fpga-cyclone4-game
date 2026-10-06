# SPDX-License-Identifier: MIT
"""051 causal early reads, latency bounds, actual pixels and immutable checkpoints."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
from build_nes_chr_residency import decode
from build_nes_trace_replay import convert
from nes_ncr1_live import expose
ROOT=Path(__file__).resolve().parents[1]
FIELDS=[('tick',32),('cpu_address',25),('ppu_address',22),('cpu_read',1),('ppu_read',1),('cpu_sample',1),('ppu_ce',1),('cpu_valid',1),('ppu_valid',1),('request',1),('ready',1),('response',1),('response_error',1),('request_address',22),('response_address',22)]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def history(log):
 rows=[];unknown=[]
 for encoded in re.findall(r'ROM HISTORY ([0-9a-fA-FxXzZ]+)',log):
  if re.search('[xXzZ]',encoded):unknown.append(encoded);continue
  value=int(encoded,16);row={}
  for key,width in reversed(FIELDS):row[key]=value&((1<<width)-1);value>>=width
  assert value==0;rows.append(row)
 return {'records':rows,'unknown_records':unknown}
def main():
 r=ROOT;raw=r/'analysis/local-rom-early-051'
 def manifest(name,status):
  count=0
  for group in ('sources','status_files','evidence'):
   for e in read(r/name)[group]:
    p=(status if group=='status_files' else r)/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];count+=1
  return count
 frozen={}
 for key,name,status,expected in [('050','rom-service','local-rom-early-051',223),('049','local-memory','local-rom-service-050',212),('048','oam-banked','local-local-memory-049',290),('047','ncr1-live','local-oam-banked-048',491),('046','ncr1-encoder','local-ncr1-live-047',107),('045','packet-memory','local-ncr1-encoder-046',121),('044_hardware','h1-hardware-044','local-packet-memory-045',23),('044_build','h1-sampling','local-h1-hardware-044',386)]:
  frozen[key]=manifest('analysis/'+name+'-artifacts.json',r/'analysis'/status/'baseline-status');assert frozen[key]==expected
 meta=read(raw/'result.json');unit=read(raw/'unit/result.json');fit=read(raw/'resource/result.json')
 assert unit['passed'] and (unit['checks'],unit['requests'],unit['negative_cases'])==(4168,525,6) and fit['phases']=={'map':0,'fit':0}
 assert sha(raw/'unit/nes_rom_early.sv')==sha(r/'src/nes/nes_rom_early.sv') and sha(raw/'unit/rom_early_tb.sv')==sha(r/'tests/nes-functional/rom_early_tb.sv')
 assert 'PASS ROM EARLY checks=4168 requests=525' in (raw/'unit/simulation.log').read_text() and 'Errors: 0, Warnings: 0' in (raw/'unit/simulation.log').read_text()
 old_driver=sha(raw/'executed-drivers/nes_rom_early-before-history-fix.py');current_driver=sha(r/'tools/nes_rom_early.py')
 ref=r/'analysis/local-rom-service-050/live';old_sources=read(ref/'result.json')['sources'];summaries=[]
 for label,delay in meta['accepted_runs'].items():
  run=raw/label;m=read(run/'result.json');assert m['passed'] and m['early_reads'] and m['delay_cycles']==delay and m['driver_sha256'] in (old_driver,current_driver)
  for n,h in m['sources'].items():assert sha(run/n)==h,(label,n)
  assert sha(run/'nes_rom_service.sv')==sha(r/'src/nes/nes_rom_early.sv')
  for n,h in old_sources.items():
   if n not in ('rtl/ppu.sv','rtl/nes.v','nes_probe.sv','nes_rom_service.sv','ncr1_live_tb.sv'):assert m['sources'][n]==h,n
  expected=expose((ref/'rtl/ppu.sv').read_text(),'PPU','output wire rom_ppu_address_valid','assign rom_ppu_address_valid=ALE && !vram_w;');assert expected==(run/'rtl/ppu.sv').read_text()
  expected=expose((ref/'rtl/nes.v').read_text(),'NES','output wire rom_cpu_address_valid,rom_ppu_address_valid','assign rom_cpu_address_valid=prg_addr[15] && prg_allow;').replace('PPU ppu(','PPU ppu(\n.rom_ppu_address_valid(rom_ppu_address_valid),');assert expected==(run/'rtl/nes.v').read_text()
  expected=expose((ref/'nes_probe.sv').read_text(),'nes_probe','output wire rom_cpu_address_valid,rom_ppu_address_valid').replace('NES core(','NES core(\n.rom_cpu_address_valid(rom_cpu_address_valid),.rom_ppu_address_valid(rom_ppu_address_valid),');assert expected==(run/'nes_probe.sv').read_text()
  if label=='live4':
   probe=raw/'delay4-probe';pm=read(probe/'result.json')
   assert not pm['passed'] and not pm['cases'] and pm['delay_cycles']==delay
   for n,h in pm['sources'].items():assert sha(probe/n)==h and m['sources'][n]==h
   assert m['recovery_driver_sha256']==sha(r/'tools/nes_rom_early_complete_probe.py')
   assert m['reused_case']==dict(case='banks32',original_result_sha256=sha(probe/'result.json'),simulation_log_sha256=sha(probe/'banks32/simulation.log'))
   assert sha(run/'banks32/simulation.log')==sha(probe/'banks32/simulation.log')
  requests=0
  for case in ('banks32','fine_x'):
   c=run/case;before=ref/case;log=(c/'simulation.log').read_text();assert 'PASS LIVE NES frames=4 bytes=8032 pixels=245760 fetches=65552' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
   requests+=int(re.search(r'ROM SERVICE requests=(\d+)',log)[1])
   assert (c/'live.tsv').read_bytes()==(before/'live.tsv').read_bytes()
   atlas=convert(bytes(int(v,16) for v in (c/'chr.hex').read_text().split())).ljust(32768,b'\0')
   for i in range(1,5):
    packet=(c/f'packet-{i}.bin').read_bytes();assert packet==(before/f'packet-{i}.bin').read_bytes()
    assert (c/f'frame-{i}.hex').read_bytes()==(before/f'frame-{i}.hex').read_bytes()
    pix=bytes(int(v,16) for v in (c/f'frame-{i}.hex').read_text().split());assert len(pix)==61440 and decode(packet,atlas)==pix
   for n in ('prg.hex','chr.hex','manifest.json'):assert sha(c/n)==sha(before/n)
  summaries.append(dict(delay_cycles=delay,frames=8,exact_pixels=491520,exact_bus_bytes=16064,exact_live_trace=True,ROM_requests=requests))
 for n,h in fit['sources'].items():assert sha(raw/'resource'/n)==h,n
 assert fit['driver_sha256']==old_driver
 for n,h in read(raw/'live2/result.json')['sources'].items():assert fit['sources'][n]==h,n
 assert sha(raw/'resource/nes_rom_service.sv')==sha(r/'src/nes/nes_rom_early.sv')
 for n,h in unit['sources'].items():assert sha(raw/'unit'/n)==h,n
 failures=[]
 for label,delay in meta['negative_runs'].items():
  run=raw/label;m=read(run/'result.json');assert m['passed'] and m['delay_cycles']==delay and m['driver_sha256']==current_driver
  for n,h in m['sources'].items():assert sha(run/n)==h,(label,n)
  assert sha(run/'nes_rom_service.sv')==sha(r/('src/nes/nes_rom_service.sv' if label=='baseline' else 'src/nes/nes_rom_early.sv'))
  for case in ('banks32','fine_x'):
   log=(run/case/'simulation.log').read_text();err=re.search(r'ROM DEADLINE/PROTOCOL error=(\d+) tick=(\d+)',log);assert err and int(err[1]) in (1,2) and '** Fatal:' in log and 'PASS LIVE NES' not in log
   h=history(log);assert len(h['records'])+len(h['unknown_records'])==16
   last=h['records'][-1];assert last['tick']==int(err[2])-1
   if int(err[1])==2:assert last['ppu_ce'] and last['ppu_read'] and not last['ppu_valid'] and 0x200000<=last['ppu_address']<0x208000
   else:assert last['cpu_sample'] and not last['cpu_valid'] and last['cpu_address']<65536
   if label=='baseline':
    assert (int(err[1]),int(err[2]))==(2,852270)
    by_tick={x['tick']:x for x in h['records']}
    assert by_tick[852264]['request'] and by_tick[852264]['request_address']==0xe187
    assert by_tick[852266]['ppu_read'] and not by_tick[852266]['ready']
    assert by_tick[852267]['request'] and by_tick[852267]['request_address']==0x201ff2
    assert last['ppu_address']==0x201ff2 and not last['response']
   failures.append(dict(run=label,case=case,delay_cycles=delay,error=int(err[1]),observed_tick=int(err[2]),decision_tick=last['tick']))
 assert read(raw/'timing-history.json')=={label:{case:history((raw/label/case/'simulation.log').read_text()) for case in ('banks32','fine_x')} for label in meta['negative_runs']}
 report=(raw/'resource/output_files/live.fit.rpt').read_text(errors='replace');summary=(raw/'resource/output_files/live.fit.summary').read_text()
 assert 'Total logic elements : 13,420 /' in summary and 'Total registers : 4895' in summary and 'Total virtual pins : 282' in summary
 assert int(re.search(r'Total LABs:.*?;\s*(\d+)',report)[1])==935 and re.search(r'; M9Ks\s*; 26 /',report)
 assert not re.search(r'Warning \((?:10036|10240)\)',(raw/'resource/map.log').read_text())
 assert not any(meta[k] for k in ('new_hardware_image','hardware_executed','timing_signoff','physical_memory_controller','CDC_implemented'))
 assert sha(r/'analysis/hardware-readiness.json')==sha(raw/'baseline-status/analysis/hardware-readiness.json')
 assert read(r/'docs/nes-development-plan.json')['hardware_tracks']==read(raw/'baseline-status/docs/nes-development-plan.json')['hardware_tracks']
 assert [x for x in read(r/'cores/registry.json')['cores'] if x['id']!='nes']==[x for x in read(raw/'baseline-status/cores/registry.json')['cores'] if x['id']!='nes']
 gbc=read(r/'source-manifest.json')['files']
 for e in gbc:assert sha(r/e['path'])==e['sha256']
 def git(*args,data=None,success=(0,)):
  p=subprocess.run(['git','-c','safe.directory='+r.as_posix(),*args],cwd=r,input=data,capture_output=True);assert p.returncode in success,(p.stdout+p.stderr).decode(errors='replace');return p.stdout
 assert not git('diff','--cached','--name-only').strip()
 assert not git('diff','HEAD','--','src/fpga','src/firmware-overlay','src/renderer','cores/gbc','release','source-manifest.json').strip();git('diff','--check')
 public=read(raw/'public-files.json')
 for n in public:
  if n.endswith('.py'):ast.parse((r/n).read_text())
 assert not git('check-ignore','-z','--stdin',data=('\0'.join(public)+'\0').encode(),success=(0,1))
 files=[p.relative_to(r).as_posix() for p in raw.rglob('*') if p.is_file()]
 assert set(git('check-ignore','-z','--stdin',data=('\0'.join(files)+'\0').encode()).decode().strip('\0').split('\0'))==set(files)
 count=manifest('analysis/rom-early-artifacts.json',r) if (r/'analysis/rom-early-artifacts.json').exists() else 0
 print(json.dumps(dict(candidate=meta['candidate'],unit_checks=4168,protocol_negative_cases=6,accepted=summaries,expected_failures=failures,joint_LE=13420,joint_LAB=935,LAB_remaining=28,joint_M9K=26,registers=4895,frozen_entries=frozen,protected_GBC_hashes=len(gbc),hardware_baseline='044 unchanged',new_hardware_image=False,physical_memory_controller=False,CDC_implemented=False,timing_signoff=False,git_diff_check='PASS',staged_files=0,allowlist='PASS',raw_ignored=len(files),manifest_entries=count),indent=2))
if __name__=='__main__':main()
