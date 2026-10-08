# SPDX-License-Identifier: MIT
"""Check frozen097 lineage, actual image bytes and host evidence; no rerun."""
from pathlib import Path
import argparse,json,re
from nes_spi_boot import ROOT,sha
from nes_diag_recovery_checks import function
from nes_cf68_pair_preflight import encode,decode
from verify_nes_native096 import NATIVE

NORMAL={'suite03':(81920,False,False,1532),'fat32-96-01':(98304,True,True,1634)}
NEGATIVE={
 'negative-config01':('config-run','b==expected'),
 'negative-crc01':('sd-crc','!safe&&!irq&&reset_held'),
 'negative-class01':('menu-crc','menu_writes097==0'),
 'negative-copy01':('menu-copy','!safe&&!irq&&reset_held'),
 'negative-report01':('report-permission','writes>0'),
}

def verify_runs(root,prefix=''):
 asm=root/(prefix+'asm01');a=json.loads((asm/'result.json').read_bytes())
 assert sha(asm/'executed-assemble097.py')==sha(ROOT/'tools/nes_config_assemble097.py')
 assert a['encoder_sha256']==sha(ROOT/'tools/nes_cf68_pair_preflight.py')
 for key,path in [('rbf','output_files/board.rbf'),('packed','fpga_n86.bi3')]:
  assert (asm/path).stat().st_size==a[key+'_bytes'] and sha(asm/path)==a[key+'_sha256']
 assert encode((asm/'output_files/board.rbf').read_bytes())==(asm/'fpga_n86.bi3').read_bytes()
 assert not a['terminal_marker_added'] and not a['new_map_fit_sta'] and not a['installable']
 for phase in ['asm','cpf']:
  text=(asm/(phase+'.log')).read_text();assert 'successful. 0 errors, 0 warnings' in text and '25.1std.0 Build 1129' in text
 previous=json.loads((ROOT/'analysis/session094-verification.json').read_bytes())
 total=0
 for name in list(NORMAL)+list(NEGATIVE):
  d=root/(prefix+name);r=json.loads((d/'result.json').read_bytes())
  assert r['assembly_sha256']==sha(asm/'result.json')
  for n,h in r['files'].items():assert sha(d/n)==h,(name,n)
  assert sha(d/'executed-driver.py')==sha(ROOT/'tools/test_nes_config097.py')
  for n in ['config097_bridge.h','config097_card.inc','config097_host.c']:
   assert sha(d/n)==sha(ROOT/'tests/nes-functional'/n)==r['inputs']['public/'+n]
  for n,record in r['image_inputs'].items():assert sha(d/n)==record['sha256'] and (d/n).stat().st_size==record['bytes']
  assert sha(d/'diag.raw')==a['rbf_sha256'] and sha(d/'diag.packed')==a['packed_sha256']
  assert sha(d/'base.packed')=='eff3f675c93a0209caf4987d72e0f277492c3dddc2b4c2aff334a667b4dbfbc7'
  assert sha(d/'menu.bin')=='f53b777a0bbe37668cd88cf8c80c5e5a0a60f861f58d1d4d3d9b082e9d1b4325'
  for n in ['diag','base']:assert decode((d/(n+'.packed')).read_bytes())==(d/(n+'.raw')).read_bytes()
  for c in r['cases']:
   p=d/(c['name']+'.log');assert sha(p)==c['log_sha256'] and c['marker'] in p.read_text()
  if name in NEGATIVE:
   mutation,assertion=NEGATIVE[name];assert r['mutation']==mutation and r['expected_failure'] and len(r['cases'])==1
   assert 'Assertion failed: '+assertion in (d/(r['cases'][0]['name']+'.log')).read_text();continue
  length,fat32,sdsc,commands=NORMAL[name]
  assert len(r['cases'])==88 and r['fat32']==fat32 and r['sdsc']==sdsc and not r['production_changed']
  for n,h in previous['host_arm_identical'].items():assert sha(d/n)==h,n
  for n,h in r['inputs'].items():
   if not n.startswith('arm04/src/'):continue
   n=n.removeprefix('arm04/src/')
   target={'ccsbcs.c':'unicode/ccsbcs.c','stm32f4xx/sdnative.c':'input-sdnative.c','stm32f4xx/spi.c':'input-spi.c','fpga.c':'input-fpga.c','fpga_spi.h':'input-fpga_spi.h','memory.c':'input-memory.c','main.c':'input-main.c'}.get(n,n)
   assert sha(d/target)==h,(name,n)
  raw=(d/'input-sdnative.c').read_text();bodies=[]
  for n in NATIVE:
   match=re.search(r'^(?:static inline void|static void|static bool|static DRESULT|int|void|bool|DRESULT|DSTATUS) '+n+r'\([^;{}]*\)\s*\{',raw,re.M);assert match
   bodies.append(function(raw[match.start():],n))
  assert (d/'native.inc').read_text()==''.join(bodies)
  raw=(d/'input-fpga.c').read_text();assert (d/'config.inc').read_text()==raw[raw.index('struct nes_diag_input {'):]
  raw=(d/'input-spi.c').read_text();assert (d/'ready.inc').read_text()==function(raw,'nes_return_spi_wait')+function(raw,'nes_return_spi_ready')
  raw=(d/'input-memory.c').read_text();start=raw.index('  if(nes_diag_active()) {\n    /* The global');end=raw.index('  } else {',start)
  assert (d/'classify.inc').read_text()=='static unsigned memory_classify097(void){\n'+raw[start:end]+'  }\nreturn 1;\n}\n'
  log=(d/'0-1.log').read_text();phases={int(p):int(n) for p,n in re.findall(r'PHASE097 phase=(\d+) commands=(\d+)',log)}
  kinds={int(p):[int(k) for k in raw.split(',') if k] for p,raw in re.findall(r'KIND097 phase=(\d+) kinds=([0-9,]+)',log)}
  assert sum(phases.values())==commands and all(len(kinds[p])==n for p,n in phases.items())
  expected={'0-1'}|{f'{n}-1' for n in list(range(1001,1014))+list(range(1101,1109))}
  for phase in [2,5,6,7,8]:
   for kind in ([1,2,3,5,6,7] if phase==8 else [2,3,6,7]):
    positions=[i+1 for i,k in enumerate(kinds[phase]) if (k==24 if kind in [1,5] else k==17 if kind in [3,7] else True)]
    expected|={f'{phase*100+kind}-{i}' for i in {positions[0],positions[(len(positions)-1)//2],positions[-1]}}
  assert {c['name'] for c in r['cases']}==expected and len(expected)==88
  assert f'frames={length*5+16} configs=2 scenario=0' in r['cases'][0]['marker']
  assert 'MENU097 copied=65536 writes=256 report_writes=5 release=1 harness_readback_commands=3' in log
  assert all(c['marker'].startswith('PASS097 ') for c in r['cases'])
  total+=len(r['cases'])
 assert total==176

def main():
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--evidence',type=Path);g.add_argument('--runs-root',type=Path);a=p.parse_args()
 if a.runs_root:verify_runs(a.runs_root.resolve(),'nes-config097-')
 else:
  e=a.evidence.resolve();m=json.loads((ROOT/'analysis/config097-verification.json').read_bytes())
  assert sha(e/'manifest.json')==m['manifest_sha256']
  files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
  for n,h in files.items():
   f=(e/n).resolve();assert f.is_relative_to(e) and sha(f)==h,n
  for n,h in (m['public_sources']|m['reused_public_sources']).items():assert sha(ROOT/n)==h,n
  old=json.loads((ROOT/'analysis/clock086-verification.json').read_bytes());assert sha(e/'prior086-manifest.json')==old['manifest_sha256']
  oldfiles=json.loads((e/'prior086-manifest.json').read_bytes())['files'];asm=json.loads((e/'asm01/result.json').read_bytes())
  assert asm['inputs']=={n.removeprefix('fit03/'):h for n,h in oldfiles.items() if n.startswith('fit03/')}
  verify_runs(e)
  assert (m['host_cases'],m['causal_controls'])==(176,5)
  assert not any(m[n] for n in ['physical','installable','new_arm','new_fit','main_whole_platform_executed','external_io_signoff'])
 print('PASS097: same086 ASM/CPF; real images;176 host cases/5 controls; menu helper lifecycle; full main/physical open')
if __name__=='__main__':main()
