# SPDX-License-Identifier: MIT
# 050 actual core -> shared synchronous ROM backend with sampling deadlines.
from pathlib import Path
import argparse,json,re,shutil,subprocess,sys,os
import nes_local_memory as local
import nes_ncr1_live as live
import nes_ncr1_live_resource as resource
ROOT=live.ROOT
CANDIDATE='NES-R1-ROM-SERVICE-050'
old_prepare=local.prepare
ROM='''
nes_rom_service rom_service(.clk(clk),.reset(reset),
 .cpumem_addr(cpumem_addr),.cpumem_read(cpumem_read),.cpu_sample(rom_cpu_sample),
 .ppumem_addr(ppumem_addr),.ppumem_read(ppumem_read),.ppu_sample(tap_ce && ppumem_read),
 .cpu_data(external_cpu_data),.ppu_data(external_ppu_data),.cpu_valid(rom_cpu_valid),.ppu_valid(rom_ppu_valid),
 .rom_ready(rom_ready),.rom_request(rom_request),.rom_address(rom_address),
 .rom_response(rom_response),.rom_error(rom_error),.rom_response_address(rom_response_address),.rom_data(rom_data),
 .fault(rom_fault),.error_code(rom_error_code));
'''
DECL='''wire rom_cpu_sample,rom_cpu_valid,rom_ppu_valid,rom_fault;
 wire [3:0] rom_error_code;
 wire rom_request;wire [21:0] rom_address;
'''
def prepare(out):
 sources=old_prepare(out)
 for n in ('nes_rom_service.sv',):shutil.copy2(ROOT/'src/nes'/n,out/n)
 p=out/'rtl/nes.v';s=live.expose(p.read_text(),'NES','output wire rom_cpu_sample',
  'assign rom_cpu_sample=(cart_ce || cpu_ce) && mr_int && prg_addr[15] && prg_allow;');live.put(p,s)
 p=out/'nes_probe.sv';s=live.expose(p.read_text(),'nes_probe','output wire rom_cpu_sample');s=s.replace('NES core(','NES core(\n.rom_cpu_sample(rom_cpu_sample),');live.put(p,s)
 p=out/'ncr1_live_tb.sv';s=p.read_text();s=s.replace(' wire frame_start',DECL+' wire frame_start',1)
 s=s.replace('reg [7:0] external_cpu_data=0,external_ppu_data=0;','wire [7:0] external_cpu_data,external_ppu_data;\n wire rom_ready,rom_response,rom_error;wire [21:0] rom_response_address;wire [7:0] rom_data;\n'+ROM+'\nrom_backend_model backend(.*);')
 a=s.index('  if(cpumem_read)external_cpu_data');b=s.index('  if(!reset)begin',a);s=s[:a]+s[b:]
 s=s.replace('  if(!reset)begin','''  if(!reset)begin
   if(rom_fault)$fatal(1,"ROM DEADLINE/PROTOCOL error=%0d tick=%0d cpu=%h ppu=%h",rom_error_code,bg_tick,cpumem_addr,ppumem_addr);
   if(rom_cpu_sample && cpumem_addr<65536 && rom_cpu_valid && cpumem_din!==prg[cpumem_addr])$fatal(1,"CPU ROM byte mismatch");
   if(tap_ce && ppumem_read && ppumem_addr>=22'h200000 && ppumem_addr<22'h208000 && rom_ppu_valid && ppumem_din!==chr[ppumem_addr[14:0]])$fatal(1,"PPU ROM byte mismatch");
''',1)
 s=s.replace('$display("PASS LIVE NES', '$display("ROM SERVICE requests=%0d",backend.accepted);\n  $display("PASS LIVE NES',1)
 live.put(p,s);shutil.copy2(ROOT/'tests/nes-functional/rom_backend_model.sv',out/'rom_backend_model.sv')
 for n in ('rtl/nes.v','nes_probe.sv','ncr1_live_tb.sv','nes_rom_service.sv','rom_backend_model.sv'):sources[n]=live.sha(out/n)
 return sources

def main():
 mode=sys.argv[1]
 if mode=='resource':
  local.prepare=prepare;live.FILES.append('nes_rom_service');old_put=resource.put
  def put(p,s):
   if p.name=='nes_live_joint.sv':
    s=s.replace('input wire [7:0] ext_cpumem_din,','input wire ext_rom_ready,ext_rom_response,ext_rom_error,\ninput wire [21:0] ext_rom_response_address,\ninput wire [7:0] ext_rom_data,\noutput wire out_rom_request,out_rom_fault,\noutput wire [21:0] out_rom_address,\noutput wire [3:0] out_rom_error_code,')
    s=s.replace('input wire [7:0] ext_ppumem_din,','')
    s=s.replace('wire [7:0] external_cpu_data=ext_cpumem_din,external_ppu_data=ext_ppumem_din;', '''wire [7:0] external_cpu_data,external_ppu_data;
wire rom_ready=ext_rom_ready,rom_response=ext_rom_response,rom_error=ext_rom_error;
wire [21:0] rom_response_address=ext_rom_response_address;
wire [7:0] rom_data=ext_rom_data;
assign out_rom_request=rom_request;assign out_rom_address=rom_address;assign out_rom_fault=rom_fault;assign out_rom_error_code=rom_error_code;
'''+DECL+ROM)
   if p.name=='live.qsf':
    s='\n'.join(x for x in s.splitlines() if not any(k in x for k in ('VIRTUAL_PIN ON -to ext_cpumem_din','VIRTUAL_PIN ON -to ext_ppumem_din')))+'\n'
    s+='\n'.join('set_instance_assignment -name VIRTUAL_PIN ON -to '+n for n in ['ext_rom_ready','ext_rom_response','ext_rom_error','ext_rom_response_address','ext_rom_data','out_rom_request','out_rom_address','out_rom_fault','out_rom_error_code'])+'\n'
   old_put(p,s)
  resource.put=put;local.main()
  out=Path(sys.argv[sys.argv.index('--out')+1]);p=out/'result.json';m=json.loads(p.read_text());m.update(candidate=CANDIDATE,driver_sha256=live.sha(Path(__file__)));live.put(p,json.dumps(m,indent=2)+'\n');return
 sys.argv.pop(1)
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);p.add_argument('--delay',type=int,default=1);a=p.parse_args()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 out=a.out.resolve();assert str(out).isascii() and not out.exists();out.mkdir();live.FILES.extend(['nes_local_memory','nes_rom_service']);sources=prepare(out)
 meta=dict(candidate=CANDIDATE,sources=sources,delay_cycles=a.delay,passed=False,cases=[],driver_sha256=live.sha(Path(__file__)))
 def save():live.put(out/'result.json',json.dumps(meta,indent=2)+'\n')
 def run(tool,args,log,cwd=out):
  with log.open('wb') as f:p=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=900)
  assert p.returncode==0,str(log)
 save();run('vlib',['work'],out/'vlib.log')
 for i,n in enumerate(live.VHDL):run('vcom',['-2008',n],out/f'vcom-{i:02}.log')
 run('vlog',['-sv','-mfcu',*live.SV,'cart_nrom.sv','nes_probe.sv',*[n+'.sv' for n in live.FILES],'rom_backend_model.sv','ncr1_live_tb.sv'],out/'vlog.log')
 for case in ('banks32','fine_x'):
  c=out/case;c.mkdir();src=ROOT/f'analysis/local-video-workloads-021/{case}/build'
  for n in ('prg.hex','chr.hex','manifest.json'):shutil.copy2(src/n,c/n)
  live.put(c/'modelsim.ini','[Library]\nwork = '+(out/'work').as_posix()+'\nothers = '+(a.questa_bin.parent/'modelsim.ini').as_posix()+'\n')
  run('vsim',['-c','-ini','modelsim.ini','work.ncr1_live_tb','+CHR32='+str(int(case=='banks32')),'+DELAY='+str(a.delay),'-do','onerror {quit -code 1}; run -all; quit -f'],c/'simulation.log',c)
  log=(c/'simulation.log').read_text();err=re.search(r'ROM DEADLINE/PROTOCOL error=(\d+) tick=(\d+)',log)
  if mode=='negative':
   assert err and int(err[1]) in (1,2),'Expected an explicit CPU/PPU deadline failure'
   meta['cases'].append(dict(case=case,expected_deadline_failure=True,error=int(err[1]),tick=int(err[2])));save()
  else:
   meta['cases'].append(live.verify_case(out,case));save();print('PASS shared-ROM '+case,flush=True)
 meta['passed']=True;save();print(json.dumps(meta['cases'],indent=2))
if __name__=='__main__':main()
