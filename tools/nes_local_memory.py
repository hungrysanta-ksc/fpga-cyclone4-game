# SPDX-License-Identifier: MIT
# 049 common initialized local RAM in actual core execution and joint resource fit.
from pathlib import Path
import argparse,json,re,shutil,subprocess,sys,os
import nes_ncr1_live as live
import nes_ncr1_live_resource as resource
import nes_oam_banked as bank
from nes_oam_compact import compact
ROOT=live.ROOT
CANDIDATE='NES-R1-LOCAL-MEMORY-049'
MEMORY='''
nes_local_memory local_memory(.clk(clk),.reset(reset_request),
 .cpumem_addr(cpumem_addr),.cpumem_write(cpumem_write),.cpumem_dout(cpumem_dout),
 .ppumem_addr(ppumem_addr),.ppumem_write(ppumem_write),.ppumem_dout(ppumem_dout),
 .external_cpu_data(external_cpu_data),.external_ppu_data(external_ppu_data),
 .cpumem_din(cpumem_din),.ppumem_din(ppumem_din),.init_done(memory_ready));
'''
def prepare(out):
 bank.bank_ppu=compact;sources=bank.prepare(out)
 shutil.copy2(ROOT/'src/nes/nes_local_memory.sv',out/'nes_local_memory.sv')
 s=(out/'ncr1_live_tb.sv').read_text()
 s=s.replace('reg queue_clk=0,host_clk=0,reset=1;', 'reg queue_clk=0,host_clk=0,reset_request=1;\n wire memory_ready;wire reset=reset_request || !memory_ready;')
 s=s.replace('reg [7:0] cpumem_din=0,ppumem_din=0;', 'wire [7:0] cpumem_din,ppumem_din;')
 s=s.replace('reg [7:0] prg[0:65535],chr[0:32767],ram[0:2047],nt[0:2047];',
  'reg [7:0] prg[0:65535],chr[0:32767];\n reg [7:0] external_cpu_data=0,external_ppu_data=0;\n'+MEMORY)
 start=s.index('  if(cpumem_read)begin');end=s.index('  if(!reset)begin',start)
 s=s[:start]+'''  if(cpumem_read)external_cpu_data<=cpumem_addr<65536?prg[cpumem_addr]:0;
  if(ppumem_read)external_ppu_data<=(ppumem_addr>=22'h200000 && ppumem_addr<(chr_32k?22'h208000:22'h204000))?chr[ppumem_addr[14:0]]:0;
'''+s[end:]
 s=s.replace('for(i=0;i<2048;i++)begin ram[i]=0;nt[i]=0;end','').replace('#20000;reset=0;','#20000;reset_request=0;')
 live.put(out/'ncr1_live_tb.sv',s)
 sources.update({n:live.sha(out/n) for n in ('nes_local_memory.sv','ncr1_live_tb.sv')});return sources

def unit(a):
 out=a.out.resolve();assert str(out).isascii() and not out.exists();out.mkdir()
 for src in ('src/nes/nes_local_memory.sv','tests/nes-functional/local_memory_tb.sv'):shutil.copy2(ROOT/src,out/Path(src).name)
 sources={p.name:live.sha(p) for p in out.iterdir()}
 for tool,args,name in [('vlib',['work'],'vlib'),('vlog',['-sv','nes_local_memory.sv','local_memory_tb.sv'],'vlog'),('vsim',['-c','local_memory_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation')]:
  with (out/(name+'.log')).open('wb') as f:p=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert p.returncode==0,name
 log=(out/'simulation.log').read_text();m=re.search(r'PASS LOCAL MEMORY checks=(\d+) complete_scrubs=3 interrupted_scrubs=1 bytes=12288',log)
 assert m and not re.search(r'\*\* (?:Fatal|Error):',log),'Inspect raw simulation.log'
 result=dict(candidate=CANDIDATE,passed=True,checks=int(m[1]),complete_scrubs=3,interrupted_scrubs=1,bytes=12288,sources=sources)
 live.put(out/'result.json',json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

def main():
 mode=sys.argv.pop(1)
 if mode!='resource':assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 if mode=='unit':
  p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);unit(p.parse_args());return
 out=Path(sys.argv[sys.argv.index('--out')+1]);live.prepare=prepare;resource.prepare=prepare
 live.FILES.append('nes_local_memory')
 if mode=='live':live.main()
 elif mode=='resource':
  old_put=resource.put
  def put(p,s):
   if p.name=='nes_live_joint.sv':
    s=s.replace('reset=ext_reset,reset_nes=ext_reset,cold_reset=ext_reset;', 'reset_request=ext_reset;\nwire memory_ready;wire reset=reset_request || !memory_ready,reset_nes=reset,cold_reset=reset;')
    start=s.index('wire cpu_ram_sel=');end=s.index('assign out_',start)
    s=s[:start]+'wire [7:0] external_cpu_data=ext_cpumem_din,external_ppu_data=ext_ppumem_din;\n'+MEMORY+s[end:]
   old_put(p,s)
  resource.put=put;resource.main()
 else:raise ValueError(mode)
 p=out/'result.json';m=json.loads(p.read_text());m.update(candidate=CANDIDATE,driver_sha256=live.sha(Path(__file__)),scope='Common 12KiB synchronous read-old-data local RAM with8192-clock reset scrub, accepted048 core/047 tap/046/045/044 pipeline. External ROM still ideal or virtual; no physical controller/PLL/loader/SNES runtime/STA or hardware.')
 live.put(p,json.dumps(m,indent=2)+'\n')
if __name__=='__main__':main()
