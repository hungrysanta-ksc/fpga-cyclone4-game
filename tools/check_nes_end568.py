# SPDX-License-Identifier: MIT
"""Run loader differential, Gray crossings and stopped-write pin checks on one seat."""
import argparse
import json
from pathlib import Path
import subprocess
from check_nes_owner562 import pin_model
from nes_raw506 import once, sha

EXTRA = '''
  // Restart loading, fault CHECK while WE is low, then present all commands.
  // The existing write has to finish exactly once, with no new grant.
  inject_fault=1;
  @(negedge mem_clk);load_begin=1;@(negedge mem_clk);load_begin=0;
  wait(load_ready);@(negedge mem_clk);load_valid=1;load_data=8'hb6;
  @(negedge mem_clk);load_valid=0;@(negedge psram_we);pulse_start=$time;
  @(negedge mem_clk);check_request=1;@(negedge mem_clk);check_request=0;
  if(!check_fault||boot_fault)$fatal(1,"CHECK fault not isolated");
  load_begin=1;load_valid=1;load_end=1;start=1;stop=1;
  @(negedge mem_clk);load_begin=0;load_valid=0;load_end=0;start=0;stop=0;
  if(!boot_fault||boot_error!=6||run_enable||check_ready||psram_we)$fatal(1,"blocked STOP");
  @(posedge psram_we);pulse_width=$time-pulse_start;
  if(pulse_width<64*5952)$fatal(1,"shortened WE");
  repeat(40)@(negedge mem_clk);
  if(memory.writes!=prior_writes+1||memory.prg[0]!=8'hb6||!psram_1ce||!psram_2ce||!psram_oe||!psram_we||run_enable)
   $fatal(1,"drain or bus ownership");
  reset=1;repeat(4)@(negedge mem_clk);reset=0;repeat(5)@(negedge mem_clk);
  if(boot_fault||check_fault||run_enable||loaded_bytes!=0)$fatal(1,"cold recovery");
  $display("PASS568 check_stop we_ps=%0d",pulse_width);
'''


def main():
    p=argparse.ArgumentParser()
    for k in ('base','board','bin','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    bench=Path(__file__).resolve().parents[1]/'tests/nes-functional'
    def run(tool,args,label):
        log=out/(label+'.log')
        with log.open('wb') as f:
            subprocess.run([str(a.bin/(tool+'.exe')),*map(str,args)],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=300,check=True)
        return log.read_text(errors='replace')
    def sim(top,label,flags=()):
        return run('vsim',['-c',top,*flags,'-do','run -all; quit -f'],label)
    run('vlib',['work'],'lib')
    loader='nes_rom_loader.sv'
    ref=out/'reference.sv';ref.write_text(once((a.base/loader).read_text(),'module nes_rom_loader #','module loader567 #'))
    candidate=a.board/loader
    src=candidate.read_text()
    late='wire reject_end_next=' in src
    defines=['+define+LATE568'] if late else (['+define+END_ONLY568'] if 'reg [1:0] reject_state;' in src else [])
    run('vlog',['-sv',*defines,ref,candidate,bench/'end568_tb.sv'],'loader-build')
    assert 'PASS568 loader=8704' in sim('end568_tb','loader')
    mutant=out/'mutant.sv'
    if late:
        mutant.write_text(once(src,'commands_blocked ? end_blocked : end_command','end_command'))
    else:
        mutant.write_text(once(src,'reject_data_state || timed_phase ||','reject_data_state ||'))
    run('vlog',['-sv',mutant],'mutant-build')
    assert '** Fatal: loader divergence' in sim('end568_tb','mutant')
    run('vlog',['-sv',a.board/'nes_domain_reset124.sv',a.board/'nes_source_epoch207.sv',bench/'epoch568_tb.sv'],'epoch-build')
    assert 'PASS568 epoch=64' in sim('epoch568_tb','epoch')
    pins=out/'pins.sv';pins.write_text(once(pin_model(bench),'assign #25 psram_data','assign #70 psram_data'))
    src=once((bench/'owner562_tb.sv').read_text(),' integer responses=',' bit inject_fault=0;time pulse_start,pulse_width;integer prior_writes;\n integer responses=')
    src=once(src,'if(boot_fault||check_fault||rom_error)','if((!inject_fault&&(boot_fault||check_fault))||rom_error)')
    src=once(src,'  $finish;','  prior_writes=memory.writes;\n'+EXTRA+'  $finish;')
    tb=out/'pins_tb.sv';tb.write_text(src)
    for i in (1,2):(out/f'reads{i}.txt').write_bytes((bench/f'owner562-reads{i}.txt').read_bytes())
    ledger={}
    for name,board in [('base',a.base),('candidate',a.board)]:
        files=[board/('nes_'+n+'.sv') for n in ('domain_reset124','native_ciram165','local_memory','rom_loader','rom_physical','rom_boot')]
        run('vlog',['-sv','+define+OWNER562',*files,pins,tb],'pins-build-'+name)
        log=sim('owner562_tb','pins-'+name,['+SMOKE'])
        assert 'PASS562 phase=2 total_reads=960 scrubs=4 writes=2' in log and 'PASS568 check_stop we_ps=' in log,name
        events=[l for l in log.splitlines() if l.startswith(('# ACCEPT562 ','# REPLY562 ','# PASS568 check_stop'))]
        assert len(events)==1931
        f=out/(name+'-events.txt');f.write_text('\n'.join(events)+'\n')
        ledger[name]=dict(sha=sha(f),we_ps=int(events[-1].split('=')[1]))
    assert ledger['base']==ledger['candidate']
    (out/'result.json').write_text(json.dumps(dict(cases=8704,edges_per_case=2,epoch=64,mutation_rejected=True,
        pins=ledger,loader=sha(candidate),reference=sha(a.base/loader),epoch_rtl=sha(a.board/'nes_source_epoch207.sv')),indent=2)+'\n')


if __name__=='__main__':main()
