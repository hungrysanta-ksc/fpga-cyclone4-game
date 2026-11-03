# SPDX-License-Identifier: MIT
"""Check OE-to-sample cycles and explicit cancel/reuse on one Questa seat."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from check_nes_owner562 import pin_model
from nes_raw506 import once,sha


def bank_testbench(bench, board):
    tb=(bench/'close561_tb.sv').read_text()
    top=(board/'nes_direct206.sv').read_text()
    # Use the fitted direct path's fault synchronizers and both local
    # reset releases. Unrelated SPI/plan/lease faults stay deasserted.
    circuit=top[top.index(' reg hf,nf;'):top.index(' wire pw,pr,ps')]
    circuit=re.sub(r'\b(hf|nf|hr|nr|hc|nc)\b',lambda m:m[1]+'565',circuit)
    circuit=circuit.replace('host_clk','hc').replace('nes_clk','nc')
    defs=' wire host_fault,nes_fault; wire transport_fault=0,spi_fault=0,batch_fault=0,lease_fault=0,core_fault=0;\n'
    defs+=' wire bulk_fault=bf,tile_fault=tf,consume_error=bad_token,command_error=cmd_error;\n'
    tb=once(tb,' nes_tile_bulk206 bulk(',defs+circuit+' nes_tile_bulk206 bulk(')
    tb=once(tb,'.stop(stop),.source_fault(tf)',".stop(1'b0),.source_fault(cancel)")
    tb=once(tb,'.reset(reset),.stop(stop),.fault(bf)',".reset(hr565),.stop(hc565),.fault(1'b0)")
    tb=once(tb,'if(tf||bf||bad_token)', 'if(tf||(bf&&!cancel)||bad_token)')
    return tb


def run(a):
    bench=Path(__file__).resolve().parents[1]/'tests/nes-functional'
    a.out.mkdir(parents=True,exist_ok=False)
    results={}
    for name,board in [('564',a.base),('565',a.board)]:
        d=a.out/name
        d.mkdir()
        def execute(tool,args,label):
            p=d/(label+'.log')
            with p.open('wb') as f:
                subprocess.run([str(a.bin/(tool+'.exe')),*map(str,args)],cwd=d,stdout=f,stderr=subprocess.STDOUT,
                               timeout=120,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
            return p.read_text(errors='replace')
        def sim(top,flags,label):
            return execute('vsim',['-c',top,*flags,'-do','run -all; quit -f'],label)
        (d/'pins.sv').write_text(once(pin_model(bench),'assign #25 psram_data','assign #70 psram_data'))
        # Keep the two-phase 480-read ownership scenarios; initialize the
        # middle of the synthetic PSRAM fixture directly for this boundary test.
        boot=(bench/'owner562_tb.sv').read_text()
        boot=once(boot,' integer responses=0,', ''' time oe_start;
 integer samples565=0;
 always @(negedge psram_oe)oe_start=$time;
 always @(posedge mem_clk)if(!dut.reader.mr && dut.reader.capture_low!==dut.reader.capture_high)
   $fatal(1,"split data capture");
 always @(posedge mem_clk)if(!dut.reader.mr && dut.reader.capture_low)begin
   if(psram_oe||!psram_we||(psram_1ce==psram_2ce)||$time-oe_start!=16*5952)
     $fatal(1,"OE/sample phase");
   samples565++;
 end
 final $display("SAMPLES565 %0d",samples565);
 integer responses=0,''')
        boot=once(boot,'  $finish;', '''  // Drop the CHECK owner while an actual pin read is active and both
  // clocks are frozen. Neither OE release nor CHECK cancellation may wait.
  check_enable=1;@(negedge mem_clk);while(!check_ready)@(negedge mem_clk);
  check_address=0;check_request=1;@(negedge mem_clk);check_request=0;
  wait(!psram_oe);#1;force clk=0;force mem_clk=0;check_enable=0;
  #1000;if(!psram_oe||!psram_we||!psram_1ce||!psram_2ce||check_response)
    $fatal(1,"owner drop with stopped clocks");
  $display("PASS565 OWNER_DROP");$finish;''')
        (d/'boot.sv').write_text(boot)
        for i in (1,2):
            (d/f'reads{i}.txt').write_text((bench/f'owner562-reads{i}.txt').read_text())
        tb=bank_testbench(bench,board)
        tb=once(tb,'  plan(1,27,9);wait(req);repeat(25)@(negedge nc);',
                '  plan(1,27,9);wait(req);repeat(25)@(negedge nc);reuse565();')
        tb=once(tb,' initial begin\n  #120000;', (bench/'reuse565.svh').read_text()+'\n initial begin\n  #120000;')
        (d/'bank.sv').write_text(tb)
        execute('vlib',['work'],'lib')
        mods=('domain_reset124','native_ciram165','local_memory','rom_loader','rom_physical','rom_boot',
              'native_mailbox206','bulk_aperture188','bulk_control194','tile205','tile_bulk206')
        execute('vlog',['-sv','+define+EARLY','+define+OWNER562',*[board/('nes_'+f+'.sv') for f in mods],
                        d/'pins.sv',d/'boot.sv',d/'bank.sv'],'compile')
        log=sim('owner562_tb',['+SMOKE'],'pins')
        assert 'PASS562 phase=2 total_reads=960 scrubs=4 writes=2' in log and 'PASS565 OWNER_DROP' in log,(name,'pins')
        sample=re.search(r'SAMPLES565 (\d+)',log)
        assert sample and int(sample[1])>=960
        events=[l for l in log.splitlines() if l.startswith(('# ACCEPT562 ','# REPLY562 '))]
        assert len(events)==1930
        (d/'bus.txt').write_text('\n'.join(events)+'\n')
        banks={}
        for phase in (0,1):
            for mode in ('clean','partial','replay'):
                label=f'{mode}{phase}'
                flags=(['+SHIFT'] if phase else [])+{'clean':[],'partial':['+PARTIAL565'],'replay':['+REPLAY']}[mode]
                log=sim('close561_tb',flags,label)
                match=re.search(r'PASS565 BANK free=(\d+) open=(\d+) ready=(\d+) replay=(\d+)',log)
                assert match,(name,label)
                banks[label]=list(map(int,match.groups()))
        results[name]=dict(events=len(events),bus=sha(d/'bus.txt'),samples=int(sample[1]),banks=banks)
    assert results['564']['bus']==results['565']['bus']
    (a.out/'result.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','board','bin','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
