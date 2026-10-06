# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,re,collections
from run_nes_h1_client import audit
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def number(pattern,text):
 match=re.search(pattern,text);assert match,pattern
 return int(match[1].replace(',',''))
def verify(root,repo):
 build=root/'build';rtl=root/'rtl';resource=root/'resource'
 bm=json.loads((build/'manifest.json').read_text());rm=json.loads((rtl/'result.json').read_text());fm=json.loads((resource/'result.json').read_text())
 assert bm['builder_sha256']==sha(repo/'tools/build_nes_h1_pattern.py')
 assert bm['rom_sha256']==sha(build/'nes-h1-pattern-033.sfc')
 assert bm['pattern_sha256']==rm['pattern_sha256']==fm['pattern_sha256']==sha(build/'h1-pattern.hex')==sha(rtl/'h1-pattern.hex')==sha(resource/'h1-pattern.hex')
 assert rm['driver_sha256']==sha(repo/'tools/nes_h1_pattern.py') and rm['passed']
 assert set(rm['phases'])=={'vlib','compile','q46_h12','q20_h10','q46_h20'} and all(v==0 for v in rm['phases'].values())
 for name,digest in rm['sources'].items():assert sha(repo/name)==sha(rtl/Path(name).name)==digest,name
 assert fm['driver_sha256']==sha(repo/'tools/nes_h1_pattern_resource.py') and fm['phases']=={'map':0,'fit':0}
 for name,digest in fm['sources'].items():assert sha(resource/name)==sha(repo/'src/nes'/name)==digest,name
 prior=json.loads((repo/'analysis/local-snes-frontend-031/resource/result.json').read_text())
 for name,digest in prior['sources'].items():assert sha(repo/'src/nes'/name)==digest,name
 pattern=b''.join((build/f'page-{n}.bin').read_bytes() for n in (1,2,3))
 assert pattern==bytes(int(x,16) for x in (build/'h1-pattern.hex').read_text().split()) and len(pattern)==6144
 for label in rm['runs']:
  log=(rtl/(label+'.log')).read_text(errors='replace')
  assert 'PASS NES H1 PATTERN checks=5 readbytes=14336' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
  assert (rtl/(label+'.bin')).read_bytes()==pattern*2+pattern[:2048]
 emulation={}
 for mode in ('normal','absent','bad_length'):
  out=root/mode;cm=json.loads((out/'capture.json').read_text())
  assert cm['exit_code']==0 and cm['rom_sha256']==bm['rom_sha256']
  assert cm['rtl_bytes_sha256']==sha(rtl/'q46_h12.bin')
  assert cm['observer_sha256']==sha(repo/'snes/video_probe/capture_h1_pattern.lua')
  allowed_runners=[repo/'tools/run_nes_h1_client.py',root/'runtime-client-runner.py',root/'auditor-failure-01/run_nes_h1_client.py']
  assert cm['runner_sha256'] in [sha(p) for p in allowed_runners]
  emulation[mode]=audit(build,rtl/'q46_h12.bin',out,mode)
 # First normal run's runner hash intentionally precedes refresh auditor correction.
 fit=(resource/'output_files/transport.fit.summary').read_text(encoding='latin-1')
 report=(resource/'output_files/transport.fit.rpt').read_text(encoding='latin-1')
 assert 'Fitter Status : Successful' in fit and 'nes_h1_pattern' in fit and 'EP4CE15F17C8' in fit
 metrics={'LE':number(r'Total logic elements\s*:\s*([\d,]+)',fit),
 'LAB':number(r'Total LABs:\s*partially or completely used\s*;\s*([\d,]+)',report),
 'M9K':number(r'; M9Ks\s*;\s*([\d,]+)',report),
 'memory_bits':number(r'Total memory bits\s*:\s*([\d,]+)',fit),
 'registers':number(r'Total registers\s*:\s*([\d,]+)',fit),
 'virtual_pins':number(r'Total virtual pins\s*:\s*([\d,]+)',fit)}
 assert metrics['memory_bits']==122880 and metrics['M9K']==20
 entities={}
 for line in report.splitlines():
  parts=[s.strip() for s in line.split(';')][1:-1]
  if len(parts)>6 and re.match(r'^\d+',parts[1]) and parts[0].strip('|') in ['nes_h1_pattern_producer:producer','nes_transport:transport','nes_packet_queue_ram:queue','nes_host_stage:stage']:
   entities[parts[0].strip('|')]={'cells':int(parts[1].split()[0]),'bits':int(parts[4]),'M9K':int(parts[5])}
 for name,bits,blocks in [('nes_h1_pattern_producer:producer',49152,8),('nes_transport:transport',73728,12),('nes_packet_queue_ram:queue',49152,8),('nes_host_stage:stage',24576,4)]:
  assert entities[name]['bits']==bits and entities[name]['M9K']==blocks
 warnings={}
 for phase in ('map','fit'):
  text=(resource/(phase+'.log')).read_text(encoding='latin-1')
  assert not re.search(r'(?m)^\s*Error \(\d+\)',text)
  warnings[phase]=dict(collections.Counter(re.findall(r'(?m)^\s*(?:Critical )?Warning \((\d+)\)',text)))
 return {'candidate':'NES-H1-PATTERN-033','passed':True,'hardware_eligible':False,
 'rtl_clock_pairs':rm['runs'],'rtl_exact_bytes':43008,'emulator':emulation,'resource':metrics,
 'entities':entities,'warning_codes':warnings,'prior031_RTL_unchanged':True,
 'limits':'Separate actual RTL bus tests and actual SNES CPU/PPU DMA with explicit Lua device model, not timing-coupled cosimulation. Virtual fit only; no boardPLL/pins/IO/CDC/STA/loader/recovery or hardware run. Diagnostic ROM image excludes NES core.',
 'verifier_sha256':sha(__file__)}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 result=verify(a.root,Path(__file__).resolve().parents[1]);a.out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'passed':result['passed'],'rtl_exact_bytes':result['rtl_exact_bytes'],'resource':result['resource'],'warning_codes':result['warning_codes']},indent=2))
