# SPDX-License-Identifier: MIT
"""Bounded exact reader comparison at qualified replies, including data delay."""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess
from test_nes_directreader165 import bench
from nes_reply181 import BASELINE, transform

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','prepared','out','questa-bin']: p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args(); assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    old=(a.baseline/'nes_rom_physical.sv').read_text()
    assert sha(a.baseline/'nes_rom_physical.sv')==BASELINE
    new=(a.prepared/'nes_rom_physical.sv').read_text(); assert new==transform(old)
    assert not a.out.exists(); a.out.mkdir()
    (a.out/'reference.sv').write_text(old.replace('module nes_rom_physical #','module baseline_physical #',1))
    tb=bench()
    assert tb.count('if(dut.rom_data!==refdut.rom_data)')==1
    tb=tb.replace('if(dut.rom_data!==refdut.rom_data)','if(dut.rom_response && dut.rom_data!==refdut.rom_data)')
    tb=tb.replace('parameter PHASE=0','parameter realtime PHASE=0').replace('#23.280423','#22.727')
    start=tb.index('module reader_last165_tb;')
    tb=tb[:start]+'''module reader_last165_tb;
wire [18:0] done;
reader_last_case #(.N(1)) a(done[0]);
reader_last_case #(.N(2)) b(done[1]);
reader_last_case #(.N(3)) c(done[2]);
generate for(genvar k=0;k<16;k++)begin:phases
 reader_last_case #(.N(16),.PHASE(k*0.375)) d(done[k+3]);
end endgenerate
initial begin wait(&done);$display("PASS REPLY181 all19");$finish;end
initial begin #1000000;$fatal(1,"REPLY181 watchdog");end
endmodule
'''
    tb=tb.replace('READLAST165','REPLY181').replace('phase=%0d','phase=%0.3f')
    (a.out/'bench.sv').write_text(tb)
    # The new data FF samples continuously, but consumers may only sample on
    # unchanged response. Propagation delay exists only in simulation copies.
    assert new.count('else reply_data<=data_hold;')==1
    delayed=new.replace(' (* preserve *) reg [7:0] reply_data;', ' wire [7:0] delayed_reply;\n assign #9.904 delayed_reply=data_hold;\n (* preserve *) reg [7:0] reply_data;').replace('else reply_data<=data_hold;','else reply_data<=delayed_reply;')
    late=delayed.replace('#9.904','#136.362')
    wrong=new.replace('else reply_data<=data_hold;', 'else if(rom_response)reply_data<=data_hold;')
    def run(tool,args,label,negative=False):
        with (a.out/(label+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=120)
        log=(a.out/(label+'.log')).read_text(errors='replace')
        if not negative: assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-1500:])
        return log
    run('vlib',['work'],'vlib')
    args=['-c','reader_last165_tb','-do','onerror {quit -code 1}; run -all; quit -f']
    result=dict(passed=False,baseline_sha256=BASELINE,candidate_sha256=sha(a.prepared/'nes_rom_physical.sv'),runs={})
    for label,source,negative in [('exact',new,False),('delay9',delayed,False),('late136',late,True),('wrong_response_capture',wrong,True)]:
        (a.out/(label+'.sv')).write_text('`timescale 1ns/1ps\n'+source)
        run('vlog',['-sv',label+'.sv','reference.sv','bench.sv'],label+'-compile')
        log=run('vsim',args,label,negative)
        if negative:
            assert '** Fatal:' in log and ('mismatch rom_data' in log or 'REPLY181 data' in log) and 'PASS REPLY181' not in log,label
            result['runs'][label]=dict(rejected=True)
        else:
            assert 'PASS REPLY181 all19' in log
            records=re.findall(r'REPLY181 N=(\d+) phase=(\S+) checks=(\d+) reads=(\d+) cancels=(\d+)',log)
            assert len(records)==19
            result['runs'][label]=dict(cases=19,reads=sum(int(r[3]) for r in records),cancels=sum(int(r[4]) for r in records),stopped_resets=19,checks=sum(int(r[2]) for r in records))
    result.update(passed=True,extra_visible_response_cycles=0,fit=False,whole_game=False,
        scope='Actual reader regs/pins/ready/ACK cycle comparison; data compared only on qualified RUN replies. CHECK remains exact. Constant PSRAM model with lane changes; no metastability, physical IO, downstream arbiter/service/full game approval.',
        sources={n:sha(Path(__file__).parent/n) for n in ['nes_reply181.py','test_nes_reply181.py','test_nes_directreader165.py']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
