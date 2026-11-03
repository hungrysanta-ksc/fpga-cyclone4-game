# SPDX-License-Identifier: MIT
"""576 routed image audit, fresh loader pulse checks and relabeled MMC558 ARM."""
import argparse,json,re,struct,zlib
from pathlib import Path
from collections import Counter
from nes_raw506 import sha
from nes_boundary575 import rows
from nes_schedule492 import funcs
from analyze_nes_owner562 import board

p=argparse.ArgumentParser()
for n in ('traces','arm','base','checks','out'):p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();root=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf8'))
prior=read(root/'analysis/cdc576-verification.json');physical=read(root/'analysis/trial558-verification.json')
d=a.traces/'nes-cdc576-board01';image=board(d)
assert image['SOF']==prior['boards']['576']['SOF']
assert image['STA']==prior['boards']['576']['board']['STA']
assert sha(d/'cdc576.sdc')==prior['boards']['576']['spec']['constraints']
assert all(sha(d/n)==h for n,h in prior['RTL'].items())
assert all(v>=0 for v in image['worst'].values())
io={}
for label,name in [('MMC558','nes-admit556-board01'),('572','nes-start572-loader'),('576','nes-cdc576-board01')]:
 path=a.traces/name;r=rows(path/'io577.tsv')
 def leg(x):return float(x['latch'])-float(x['launch'])-float(x['slack'])
 output={k:round(max(leg(x) for x in r if x['group']=='output' and x['to'].startswith(k)),3)
         for k in ['SPI_MISO','MCU_RDY','SNES_DATA','SNES_DATABUS_OE','SNES_DATABUS_DIR']}
 output['SNES_raw_pin_max']=max(float(x['data_delay']) for x in rows(path/'bus571.tsv'))
 output['loader_output_max']=round(max(leg(x) for x in r if x['group']=='loader_output'),3)
 uc=(path/'implementation-unconstrained204.rpt').read_text()
 ports={}
 for mode in ('Input','Output'):
  title=re.search(r'^; Unconstrained '+mode+r' Ports\s+;\s*$',uc,re.M)
  assert title
  section=uc[title.end():].split('; Unconstrained ')[0]
  pins=re.findall(r'^; ([A-Z][A-Z0-9_]*(?:\[\d+\])?)\s*;',section,re.M)
  ports[mode]=dict(Counter(re.sub(r'\[\d+\]','',s) for s in pins))
 assert sum(ports['Input'].values())==54 and sum(ports['Output'].values())==57
 io[label]=dict(maximum_leg_ns=output,unconstrained_ports=ports,
   reports={n:sha(path/n) for n in ['io577.tsv','bus571.tsv','loader577.tsv','implementation-unconstrained204.rpt']})
assert io['MMC558']['unconstrained_ports']==io['576']['unconstrained_ports']
timer=rows(d/'loader577.tsv')
assert len(timer)==42 and all(float(x['slack'])>=0 for x in timer)
pulse=read(a.traces/'nes-pulse577-test02/result.json')
assert pulse['loader']==sha(d/'nes_rom_loader.sv')
assert len(pulse['phases'])==2
for r in pulse['phases']:
 assert 'cases=8320 writes=7308 busy_END=130 blocked_END=130 setup_ps=130944 write_ps=380928 hold_ps=130944' in r['line']
new=a.arm/'obj-nes-100';old=a.base/'obj-nes-100'
assert sha(old/'firmware.stm')==physical['firmware_SHA256']
before=(old/'firmware.stm').read_bytes();after=(new/'firmware.stm').read_bytes()
assert funcs(new/'sd2snes.elf')==funcs(old/'sd2snes.elf')
assert before[32:].replace(b'558',b'577')==after[32:]
n,c,inv=struct.unpack_from('<III',after,8)
assert after[:4]==b'STM3' and len(after)==n+512<=0x34000 and c==zlib.crc32(after[512:]) and c^inv==0xffffffff
checks={k:read(a.checks/(k+'.json')) for k in ('windows','credit','transport','menu')}
assert checks['windows']['firmware_SHA256']==sha(new/'firmware.stm')
assert checks['windows']['reset'] and checks['windows']['unfinished_excluded']
assert [(r['start_s'],r['end_s'],r['displays']) for r in checks['windows']['accepted']]==[(5,40,2),(40,55,2)]
assert checks['credit']['sha']==sha(new/'firmware.stm') and checks['credit']['rows']==physical['credit']['rows']
assert checks['transport']['firmware']==sha(new/'firmware.stm') and checks['transport']['rows']==read(root/'analysis/supply549-verification.json')['builds']['suffix']['first_batch_guards']
assert checks['menu']['firmware']==sha(new/'firmware.stm') and all(v['released']==int(k=='normal') for k,v in checks['menu']['rows'].items())
recover={}
for fault in ('none','program','done','busy','token'):
 r=read(a.checks/f'base-{fault}/result.json')
 assert r['passed'] and r['firmware_sha256']==sha(new/'firmware.stm')
 assert r['safe_return']==r['base_restored']==int(fault=='none')
 assert r['config_paths']==['/sd2snes/fpga_mmc577.bi3','/sd2snes/fpga_base.bi3']
 recover[fault]=r
programmer=read(a.traces/'nes-gate577-programmer01/result.json')
assert programmer['passed']
out=dict(candidate='MMC577',gate='limited physical trial only',new_FPGA_FIT=False,physical_verified=False,
 timing_policy='576 exact CDC bounds and timed synchronous consumers; original raw STA preserved, not identical to MMC558 raw SDC',
 board=image,loader_path=timer,pulse=pulse,io=io,
 firmware_SHA256=sha(new/'firmware.stm'),identical_functions=len(funcs(new/'sd2snes.elf')),
 Flash_B=len(after),Flash_free_B=0x34000-len(after),BSS_B=checks['windows']['BSS_B'],
 checks=checks,base_return=recover,programmer=programmer,schedule=prior['schedule'],
 raw_STA=prior['boards']['576']['raw_worst'],
 scope='No new board timing exceptions or circuit changes. 576 SOF unchanged; labeled ARM code byte-identical to MMC558. GPIO/DONE/IRQ/IO are modeled in ARM tests. Fresh pulse RTL uses normal input sequences, no forced internal state. External path inventory is not a receiver setup/hold specification.',
 unresolved=['Minimum synchronous setup +0.045ns; all three modeled corners positive, no safety margin guarantee.',
 'SNES combinational pin inventory 28.620 -> 31.892ns (+3.272); not external electrical signoff.',
 '54 input / 57 output ports lack complete min/max external constraints; DAC and PCB/receiver limits still open.',
 'No new physical FPS or physical menu recovery result. Request same route and 5-40 / 40-55s logs.'])
a.out.write_text(json.dumps(out,indent=2)+'\n',newline='\n')
print('PASS577 gate',len(after),len(funcs(new/'sd2snes.elf')),image['worst'])
