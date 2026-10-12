# SPDX-License-Identifier: MIT
"""Actual target-ROM execution with same-edge CHR capture; optional passive replay."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,ROM_SHA,VHDL,SV,EXTRA,sha
from nes_native_tap165 import prepare,BINDING,NEW

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence','rom','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--frames',type=int,default=20)
 p.add_argument('--passive-control',action='store_true',help='Optional full boot replay; not required for the observational-only wiring change')
 a=p.parse_args();assert 8<=a.frames<=120
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost' and sha(a.rom)==ROM_SHA
 inputs=prepare(a.evidence,a.out)
 for n in ['tests/nes-functional/native_tap165_checks.svh']:
  shutil.copy2(ROOT/n,a.out/Path(n).name)
 text=(ROOT/'tests/nes-functional/game147_tb.sv').read_text()
 def replace(old,new):
  nonlocal text
  assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
 replace('module game147_tb;','module native_tap165_tb;')
 replace('wire rom_cpu_address_valid,rom_ppu_address_valid,rom_cpu_sample;',
   'wire [13:0] native_chr_logical;\nwire [21:0] game148_hint_physical;\nwire [63:0] ppu_fault_state154;\nwire game147_prefetch_hint,game160_restart_hint;\nwire rom_cpu_address_valid,rom_ppu_address_valid,rom_cpu_sample;')
 replace('nes_rom_early rom_service(','''nes_rom_early rom_service(
 .ppu_prefetch_valid(game147_prefetch_hint && (game160_restart_hint || rom_ppu_valid || (ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800))),.ppu_prefetch_address(game148_hint_physical),''')
 replace(');$finish;',');verify_native();')
 replace('endmodule','`include "native_tap165_checks.svh"\n'+BINDING.replace('.ppu_valid(rom_ppu_valid)', '.ppu_valid(rom_ppu_valid && !control)')+'\nendmodule')
 # The included file only monitors/leases the cache. Core clocks, CPU and PPU
 # state are never forced. Disabling sample_valid is the passive comparison.
 (a.out/'native_tap165_tb.sv').write_text(text,encoding='utf8')
 image=a.rom.read_bytes()
 for name,b in [('prg',image[16:0x40010]),('chr',image[0x40010:])]:
  (a.out/(name+'.hex')).write_text(''.join(f'{v:02x}\n' for v in b))
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=2400)
  s=(a.out/(label+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4000:]
  return s
 run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 run('vlog',['-sv','-mfcu',*SV,*EXTRA,'nes_live_joint.sv',*[Path(n).name for n in NEW],'native_tap165_tb.sv'],'vlog')
 runs=[]
 for control in ([0,1] if a.passive_control else [0]):
  label=f'core-control{control}'
  s=run('vsim',['-c','work.native_tap165_tb',f'+FRAMES={a.frames}',f'+CONTROL={control}',
   '-do','onerror {quit -code 1}; run -all; quit -f'],label)
  m=re.search(r'NATIVE165 frames=(\d+) captured=(\d+) banks=(\d+) complete=(\d+) partial=(\d+) empty=(\d+) queries=(\d+) cpu=(\d+) ppu=(\d+) pixel=([0-9a-f]+) bus=([0-9a-f]+)',s)
  assert m and f'PASS NATIVE165 actual PPU binding control={control}' in s,s[-3000:]
  row=dict(zip(['frames','captured','bank_changes','complete','partial','empty','queries','cpu_reads','ppu_reads'],map(int,m.groups()[:9])))
  row.update(pixel_hash=m[10],bus_hash=m[11],control=control,log_sha256=sha(a.out/(label+'.log')))
  runs.append(row);print(row,flush=True)
 if a.passive_control:
  for k in ['frames','queries','cpu_reads','ppu_reads','pixel_hash','bus_hash']:assert runs[0][k]==runs[1][k],k
 result=dict(passed=True,rom_sha256=ROM_SHA,inputs=inputs,runs=runs,
  generated_sources={n:sha(a.out/n) for n in VHDL+SV+EXTRA+['nes_live_joint.sv','native_tap165_tb.sv']},
  public_sources={n:sha(ROOT/n) for n in NEW+['tools/nes_native_tap165.py','tools/test_nes_native_tap165.py','tests/nes-functional/native_tap165_checks.svh']},
  passive_control_executed=a.passive_control,
  hardware=False,scope='Actual CPU/PPU/MMC3/70ns reader executing SMB3 boot without forced core state. Preloaded memory, no buttons. Same-edge cache; optional passive replay only if explicitly recorded. Joint wrapper generated and compiled but not instantiated; no host CDC/SNES consumer/fit or physical frame-rate proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS actual PPU capture')
if __name__=='__main__':main()
