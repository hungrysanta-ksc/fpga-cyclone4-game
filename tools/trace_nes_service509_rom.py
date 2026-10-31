# SPDX-License-Identifier: MIT
"""Actual507 CPU/PPU/MMC3+cache+arbiter+READ16 trace under saturated fill.

Boot scenes, not geometry230 first-level workload. No source or board edits.
The 70ns PSRAM is modeled. Paired no-fill run proves core observations intact.
"""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from nes_functional import VHDL,SV,sha
from nes_raw506 import once
ROOT=Path(__file__).resolve().parents[1]
EXTRA=['cart_nrom.sv','nes_probe.sv','nes_rom_service.sv','nes_local_memory.sv','nes_rom_physical.sv','nes_domain_reset124.sv','nes_native_arbiter165.sv','nes_native_ciram165.sv']
def prepare(a):
    a.out.mkdir(parents=True,exist_ok=False);pins={}
    for n in VHDL+SV+EXTRA:
        p=a.out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.board/n,p);pins[n]=sha(p)
    for n in ['prg.hex','chr.hex']:shutil.copy2(a.rom_data/n,a.out/n);pins[n]=sha(a.out/n)
    s=(ROOT/'tests/nes-functional/game147_tb.sv').read_text()
    s=once(s,'frame=0,','')
    s=once(s,'module game147_tb;','module trace509_tb;\nparameter FILL=0;\nstring folder;integer tracefd,anchorfd,frame=0;')
    header=(a.board/'nes_probe.sv').read_text().split(');',1)[0].split('module nes_probe(',1)[1]
    declarations=[]
    for port in re.split(r',\s*(?=(?:input|output)\b)',header):
        m=re.fullmatch(r'\s*(input|output)\s+wire\s*(\[[^]]+\])?\s*(.*?)\s*,?\s*',port,re.S);assert m,port
        for name in m[3].split(','):
            name=name.strip();assert re.fullmatch(r'\w+',name),name
            if not re.search(r'\b'+name+r'\b',s):declarations.append('wire '+(m[2]or'')+' '+name+('=0'if m[1]=='input'else'')+';')
    s=once(s,' nes_probe dut(.*);','\n'.join(declarations)+'\n nes_probe dut(.*);')
    s=once(s,' nes_rom_early rom_service(','''wire native_core_safe;
 nes_rom_early rom_service(.native_core_safe(native_core_safe),
 .ppu_prefetch_valid(game147_prefetch_hint && (game160_restart_hint || rom_ppu_valid || (ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800))),.ppu_prefetch_address(game148_hint_physical),''')
    start=s.index(' nes_rom_physical #');end=s.index(' reg [7:0] prg',start)
    physical=s[start:end]
    for n in ['ready','request','address','response','error','response_address','data']:physical=physical.replace('(rom_'+n+')','(mem_'+n+')')
    s=s[:start]+'''wire mem_ready,mem_request,mem_response,mem_error;wire[21:0]mem_address,mem_response_address;wire[7:0]mem_data;
wire fill_ready,fill_idle,fill_response,fill_error,arbiter_fault;
wire[21:0] fill_response_address;wire[15:0]fill_response_generation;wire[7:0]fill_data;
reg[21:0]fill_address=22'h200000;reg[21:0]held;integer granted=0,replied=0,grant_tick=0;
wire fill_request=FILL && frame>=12;
nes_native_arbiter165 arbiter(.clk(clk),.reset(reset),.slot(native_fill_slot),.core_safe(native_core_safe),
 .core_request(rom_request),.core_address(rom_address),.core_ready(rom_ready),.core_response(rom_response),.core_error(rom_error),.core_response_address(rom_response_address),.core_data(rom_data),
 .fill_request(fill_request),.fill_abort(1'b0),.fill_address(fill_address),.fill_generation(16'd509),.fill_ready(fill_ready),.fill_idle(fill_idle),.fill_response(fill_response),.fill_error(fill_error),.fill_response_address(fill_response_address),.fill_response_generation(fill_response_generation),.fill_data(fill_data),
 .mem_ready(mem_ready),.mem_request(mem_request),.mem_address(mem_address),.mem_response(mem_response),.mem_error(mem_error),.mem_response_address(mem_response_address),.mem_data(mem_data),.fault(arbiter_fault));
'''+physical+s[end:]
    s=once(s,'  ticks++;','''  ticks++;
  if(arbiter_fault)$fatal(1,"arbiter fault");
  if(fill_request&&fill_ready)begin
   if(granted!=replied||!native_fill_slot||!native_core_safe||rom_request)$fatal(1,"bad admission");
   held=fill_address;grant_tick=ticks;granted++;
   $fwrite(tracefd,"G %0d %0d %0d %0d %06h\\n",ticks,frame,scanline,cycle,held);
  end
  if(fill_response)begin
   if(replied+1!=granted||fill_error||fill_response_generation!=509||fill_response_address!==held||fill_data!==chr[held[16:0]]||ticks-grant_tick>7)$fatal(1,"fill response");
   replied++;fill_address<=fill_address==22'h21ffff ? 22'h200000 : fill_address+1;
   $fwrite(tracefd,"R %0d %0d %0d %0d %06h\\n",ticks,frame,scanline,cycle,held);
  end''')
    s=once(s,'frame++;pixels=0;','frame++;pixels=0;$fwrite(anchorfd,"%0d %0d\\n",frame,ticks);')
    s=once(s,'$sformatf("game-%0d.hex",frame)','$sformatf("%s/game-%0d.hex",folder,frame)')
    s=once(s,'     $display("PASS GAME147', '     if(FILL && replied<1000)$fatal(1,"missing fill coverage");\n     $fclose(tracefd);$fclose(anchorfd);$display("PASS TRACE509 fills=%0d",replied);\n     $display("PASS GAME147')
    s=once(s,'  unused=$value$plusargs("FRAMES=%d",target);','  unused=$value$plusargs("OUT=%s",folder);tracefd=$fopen({folder,"/rom.tsv"},"w");anchorfd=$fopen({folder,"/anchors.tsv"},"w");\n  unused=$value$plusargs("FRAMES=%d",target);')
    (a.out/'trace509_tb.sv').write_text(s,encoding='utf8',newline='\n')
    shutil.copy2(ROOT/'tests/nes-functional/native_arbiter165_tb.sv',a.out/'native_arbiter165_tb.sv')
    (a.out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');print('Prepared exact507 core/cache/arbiter/reader inputs')
def run(a):
    def call(exe,args,label):
        with(a.out/(label+'.log')).open('wb')as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
        text=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-3000:]
        return text
    call('vlib',['work'],'lib')
    for i,n in enumerate(VHDL):call('vcom',['-2008',n],f'vcom{i}')
    call('vlog',['-sv','-mfcu',*SV,*EXTRA,'trace509_tb.sv','native_arbiter165_tb.sv'],'compile')
    reports=[]
    for fill in [0,1]:
        folder=a.out/f'fill{fill}';folder.mkdir()
        log=call('vsim',['-L','altera_mf_ver','-c','work.trace509_tb',f'-gFILL={fill}',f'+FRAMES={a.frames}',f'+OUT=fill{fill}','-do','onerror {quit -code 1};run -all;quit -f'],f'fill{fill}')
        assert 'PASS TRACE509'in log;reports.append(re.search(r'PASS GAME147.*',log)[0]);print(f'PASS509 core fill={fill}',flush=True)
    assert reports[0]==reports[1],reports
    for p in (a.out/'fill0').glob('game-*.hex'):assert sha(p)==sha(a.out/'fill1'/p.name),p.name
    guard=call('vsim',['-c','work.native_arbiter165_tb','-gPHASE=3.5','-do','onerror {quit -code 1};run -all;quit -f'],'guards');assert 'PASS ARBITER165'in guard
    r=dict(passed=True,scope=__doc__,frames=a.frames,core_observation=reports[0],source_pins=json.loads((a.out/'pins.json').read_text()),testbench_SHA256=sha(a.out/'trace509_tb.sv'),trace_SHA256=sha(a.out/'fill1/rom.tsv'),anchors_SHA256=sha(a.out/'fill1/anchors.tsv'),guard_PASS=re.search(r'PASS ARBITER165.*',guard)[0])
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS509 paired core trace and original STOP/drain/error guards')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','run'])
    for n in ['board','rom-data','out','questa-bin']:p.add_argument('--'+n,type=Path)
    p.add_argument('--frames',type=int,default=20);a=p.parse_args();(prepare if a.mode=='prepare'else run)(a)
