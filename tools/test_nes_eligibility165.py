# SPDX-License-Identifier: MIT
"""Compare READY eligibility and connected SPI/boot/reader against prior RTL."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_eligibility165 import loader,boot,physical,TAG_OLD,TAG_NEW
from test_nes_check165 import REGS

def unit():
    return '''`timescale 1ns/1ps
module eligibility165_tb;
reg mem_clk=0,reset=0;
nes_rom_loader dut(.mem_clk(mem_clk),.reset(reset),.load_begin(1'b0),.load_chr32(1'b0),.load_valid(1'b0),.load_end(1'b0),.start(1'b0),.stop(1'b0),.load_data(8'd0),.commands_blocked(1'b0));
baseline_loader refdut(.mem_clk(mem_clk),.reset(reset),.load_begin(1'b0),.load_chr32(1'b0),.load_valid(1'b0),.load_end(1'b0),.start(1'b0),.stop(1'b0),.load_data(8'd0),.commands_blocked(1'b0));
integer combinations=0;
reg enable,request,failed;
initial begin
 for(integer st=0;st<16;st++)for(integer release_bits=0;release_bits<4;release_bits++)for(integer fault=0;fault<2;fault++)begin
  dut.state=st;refdut.state=st;dut.release_reset=release_bits;refdut.release_reset=release_bits;
  dut.fault=fault;refdut.fault=fault;#1;
  if(dut.check_loaded !== (refdut.loaded && !refdut.run_enable && !refdut.fault))$fatal(1,"ELIGIBILITY165 loader output");
  for(integer flags=0;flags<8;flags++)begin
   {enable,request,failed}=flags;#1;
   if((enable && dut.check_loaded && !failed) !== (enable && refdut.loaded && !refdut.run_enable && !refdut.fault && !failed))$fatal(1,"ELIGIBILITY165 active");
   if(((enable||request)&&!dut.check_loaded) !== ((enable||request)&&(refdut.run_enable||!refdut.loaded||refdut.fault)))$fatal(1,"ELIGIBILITY165 fault condition");
   combinations++;
  end
 end
 $display("PASS ELIGIBILITY165 combinations=%0d",combinations);$finish;
end
endmodule
'''

def connected():
    s=(ROOT/'tests/nes-functional/tag165_tb.sv').read_text()
    at=s.index(' nes_rom_boot boot(');end=s.index(' integer edges=',at)
    ref=s[at:end].replace('nes_rom_boot boot(','baseline_boot refboot(',1)
    outputs='check_ready check_response check_response_address check_data check_fault load_ready loaded run_enable boot_fault boot_error loaded_bytes rom_chr32 rom_ready rom_response rom_error rom_response_address rom_data psram_address psram_1ce psram_2ce psram_oe psram_we psram_bhe psram_ble'.split()
    for n in outputs:
        ref,count=re.subn(r'\.'+n+r'\([^)]*\)','.'+n+'()',ref);assert count==1,n
    s=s[:end]+ref+s[end:]
    for text in ['state=4','loaded_bytes=19\'h60000','count_complete=1']:
        needle='boot.loader.'+text+';';assert s.count(needle)==1
        s=s.replace(needle,needle+'refboot.loader.'+text+';')
    compare='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"ELIGIBILITY165 SPI {n}");' for n in REGS+['pending_counter_clear','pending_counter_inc'])
    compare+='\n'+'\n'.join(f'if(boot.{n}!==refboot.{n})$fatal(1,"ELIGIBILITY165 boot {n}");' for n in outputs)
    s=s.replace('// COMPARE_ALL_REGISTERS',compare)
    needle='  $display("PASS TAG165 edges='
    assert s.count(needle)==1
    extra='''  // Loader fault is the actual start point of the targeted timing path.
  for(integer phase=0;phase<24;phase++)begin
   begin_check(19'h12345);request();repeat(phase)tick();
   boot.loader.fault=1;refboot.loader.fault=1;repeat(28)tick();
   if(!fault||error_code!=9||check_enable||dut.check_busy||!psram_oe)$fatal(1,"ELIGIBILITY165 loader fault response");
  end
  // Fault before CHECK_BEGIN must remain lifecycle error6, not begin CHECK.
  fresh();boot.loader.fault=1;refboot.loader.fault=1;
  frame(8'h66,0,0);repeat(12)tick();
  if(!fault||error_code!=6||check_enable)$fatal(1,"ELIGIBILITY165 begin fault");
  // Fault after READ frame transmission, before SS capture/retirement.
  begin_check(19'h12345);frame(8'h67,24'h012345,0);
  boot.loader.fault=1;refboot.loader.fault=1;repeat(28)tick();
  if(!fault||error_code!=9||check_request)$fatal(1,"ELIGIBILITY165 capture fault");
  $display("PASS ELIGIBILITY165 loader_fault_cases=26");
'''
    return s.replace(needle,extra+needle)

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','tag-test','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    t=json.loads((a.tag_test/'result.json').read_bytes());assert t['passed']
    m=json.loads((a.prepared/'preparation.json').read_bytes());a.out.mkdir()
    # Only the corrected ownership comment differs from the tested SPI bytes.
    assert (a.prepared/'nes_rom_spi.sv').read_text()==(a.tag_test/'candidate.sv').read_text().replace(TAG_OLD,TAG_NEW)
    assert sha(a.tag_test/'candidate.sv')==t['source_sha256']
    assert (a.prepared/'nes_rom_loader.sv').read_text()==loader((a.baseline/'nes_rom_loader.sv').read_text())
    assert (a.prepared/'nes_rom_boot.sv').read_text()==boot((a.baseline/'nes_rom_boot.sv').read_text())
    assert (a.prepared/'nes_rom_physical.sv').read_text()==physical((a.baseline/'nes_rom_physical.sv').read_text())
    for n in ['nes_rom_spi.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:
        assert sha(a.prepared/n)==m['sources'][n];(a.out/n).write_bytes((a.prepared/n).read_bytes())
    (a.out/'reference_spi.sv').write_text((a.baseline/'nes_rom_spi.sv').read_text().replace('module nes_rom_spi_check(','module baseline_check165(',1))
    (a.out/'reference_loader.sv').write_text((a.baseline/'nes_rom_loader.sv').read_text().replace('module nes_rom_loader #','module baseline_loader #',1))
    (a.out/'reference_boot.sv').write_text((a.baseline/'nes_rom_boot.sv').read_text().replace('module nes_rom_boot(','module baseline_boot(',1).replace('nes_rom_loader loader(','baseline_loader loader(',1).replace('nes_rom_physical #','baseline_physical #',1))
    (a.out/'reference_physical.sv').write_text((a.baseline/'nes_rom_physical.sv').read_text().replace('module nes_rom_physical #','module baseline_physical #',1))
    (a.out/'eligibility165_tb.sv').write_text(unit());(a.out/'tag165_tb.sv').write_text(connected())
    def run(tool,args,label,expected=None):
        with (a.out/(label+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
        log=(a.out/(label+'.log')).read_text(errors='replace')
        if expected:assert expected in log and 'PASS ELIGIBILITY165' not in log,(label,log[-2000:])
        else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2000:])
        return log
    run('vlib',['work'],'vlib')
    files=['nes_rom_spi.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','reference_spi.sv','reference_loader.sv','reference_boot.sv','reference_physical.sv','eligibility165_tb.sv','tag165_tb.sv']
    run('vlog',['-sv',*files],'compile')
    def sim(top):return ['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f']
    u=run('vsim',sim('eligibility165_tb'),'unit');assert 'PASS ELIGIBILITY165 combinations=1024' in u
    seq=run('vsim',sim('tag165_tb'),'sequential');assert 'reads=124 acks=7 corruptions=19 cancels=72 overlaps=2' in seq and 'loader_fault_cases=26' in seq
    text=(a.prepared/'nes_rom_loader.sv').read_text();needle='assign check_loaded=!active_reset && !fault && state==READY;'
    assert text.count(needle)==1
    (a.out/'wrong_fault.sv').write_text(text.replace(needle,'assign check_loaded=!active_reset && state==READY;'))
    run('vlog',['-sv','wrong_fault.sv'],'wrong-compile')
    run('vsim',sim('eligibility165_tb'),'wrong-negative','ELIGIBILITY165 loader output')
    sources=['tools/nes_eligibility165.py','tools/test_nes_eligibility165.py','tests/nes-functional/tag165_tb.sv','tools/test_nes_check165.py']
    result=dict(passed=True,eligibility_combinations=1024,loader_fault_cases=26,
        sequential_summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0],missing_fault_rejected=True,
        sources={n:sha(a.prepared/n) for n in ['nes_rom_spi.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']},
        spi_reuse_result_sha256=sha(a.tag_test/'result.json'),spi_reuse_states=t['conditional_states'],spi_reuse_captures=t['captures'],
        spi_reuse_normalization='Only the one corrected ownership comment; executable SPI text unchanged.',
        public_sources={n:sha(ROOT/n) for n in sources})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
