# SPDX-License-Identifier: MIT
"""Isolate real-ROM reference PPUMASK writes at exact178 admission boundary.

All other raster inputs are held constant. Missing-fetch tests are explicitly
synthetic. This does not identify all errors of the real FPGA level frame.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha


def cases(trace):
    rows=[line.split() for line in trace.read_text().splitlines()]
    writes=[(int(f),int(y),int(x),int(v,16)) for f,y,x,a,v in rows if a=='2001']
    result=[]
    for frame in [350,480,620,650,699]:
        raw=[(y,x,v) for f,y,x,v in writes if f==frame]
        # endFrame callback is at the end of the visible frame: writes in
        # vblank precede y0 within this Lua counter bucket. Preserve that order.
        assert raw and raw[0][0]>=240
        initial=None;events=[];visible_started=False
        for y,x,v in raw:
            if y>=240 or y<0:
                assert not visible_started
                initial=v
            else:visible_started=True;events.append((y,x,v))
        assert initial is not None and events==sorted(events)
        for delay in [0,1,3]:
            # Reference callback write time is not an FPGA-effective PPU time.
            # Exercise small positive offsets rather than claim exact alignment.
            shifted=[(y+(x+delay)//341,(x+delay)%341,v) for y,x,v in events]
            expected=0 if frame in [350,480] else 0x48 if frame==620 and delay else 8
            result.append(dict(frame=frame,offset=delay,initial=initial,events=shifted,
                               expect_error=expected))
    return result


def bench(data):
    source='''`timescale 1ns/1ps
module level179_raster_tb;
reg clk=0,reset=1,ppu_ce=0,release_packet=0;
always #5 clk=~clk;
reg [8:0] scanline=0,dot=0;reg [7:0] display_mask=0;
wire owned,valid;wire [7:0] errors,row_count;wire [5:0] palette_count;
nes_native_raster_frame165 dut(.clk(clk),.reset(reset),.ppu_ce(ppu_ce),.scanline(scanline),.dot(dot),
 .scroll_v(15'd0),.scroll_t(15'd0),.fine_x(3'd0),.pattern_mode(3'd0),.display_mask(display_mask),
 .palette(192'd0),.scroll_access(1'b0),.source_fault(1'b0),.release_packet(release_packet),
 .query(1'b0),.query_palette(1'b0),.query_row(8'd0),.query_bank(5'd0),.query_color(5'd0),
 .scroll_seen(),.owned(owned),.valid(valid),.generation(),.errors(errors),.row_count(row_count),.palette_count(palette_count),.response(),.hit(),.data());
task automatic run_frame(input integer test_id,input integer initial_mask,input integer expected);
 @(negedge clk);release_packet=1;ppu_ce=0;
 @(negedge clk);release_packet=0;display_mask=initial_mask;
 for(integer y=0;y<=232;y++)for(integer x=0;x<341;x++)begin
  scanline=y;dot=x;
  case(test_id)
EVENTS
  endcase
  ppu_ce=1;@(negedge clk);ppu_ce=0;repeat(3)@(negedge clk);
 end
 if(!owned || errors!==expected[7:0] || valid!==(expected==0) || row_count!=224 || palette_count!=1)
  $fatal(1,"case %0d error=%02h expected=%02h valid=%b rows=%0d",test_id,errors,expected,valid,row_count);
 $display("RASTER179 case=%0d valid=%0d errors=%02h rows=%0d",test_id,valid,errors,row_count);
endtask
initial begin
 repeat(3)@(negedge clk);reset=0;
RUNS
 $display("PASS RASTER179 cases=COUNT");$finish;
end
initial begin #100000000;$fatal(1,"watchdog");end
endmodule
'''
    ev=[];runs=[]
    for i,c in enumerate(data):
        changes=''.join(f"if(y=={y}&&x=={x})display_mask=8'h{v:02x};" for y,x,v in c['events'])
        ev.append(f'{i}:begin {changes} end')
        runs.append(f"run_frame({i},{c['initial']},{c['expect_error']});")
    # A clean worldmap-like mask-only frame after the rejected level sequence.
    runs.append('run_frame(999,24,0);')
    return source.replace('EVENTS','\n'.join(ev)).replace('RUNS','\n'.join(runs)).replace('COUNT',str(len(runs)))


def main():
    p=argparse.ArgumentParser()
    for n in ['deployed','reference','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    assert not a.out.exists();a.out.mkdir()
    pins=json.loads((a.deployed.parent/'manifest01.json').read_bytes())
    sources={}
    for n in ['nes_native_raster_frame165.sv','nes_native_compact_planes165.sv']:
        assert sha(a.deployed/n)==pins['sources/'+n];shutil.copy2(a.deployed/n,a.out/n);sources[n]=sha(a.out/n)
    ref=json.loads((a.reference/'result.json').read_bytes());assert ref['trace_sha256']==sha(a.reference/'writes.tsv')
    data=cases(a.reference/'writes.tsv')
    (a.out/'cases.json').write_text(json.dumps(data,indent=2)+'\n')
    (a.out/'level179_raster_tb.sv').write_text(bench(data),encoding='utf8',newline='\n')
    compact=ROOT/'tests/nes-functional/level179_compact_gap_tb.sv';shutil.copy2(compact,a.out/compact.name)
    def call(exe,args,label):
        with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
        text=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-2500:]
        return text
    call('vlib',['work'],'vlib')
    call('vlog',['-sv',*sources,'level179_raster_tb.sv',compact.name],'vlog')
    for name,marker in [('raster','PASS RASTER179 cases=16'),('compact_gap','PASS COMPACT179 cases=5')]:
        text=call('vsim',['-c','work.level179_'+name+'_tb','-do','onerror {quit -code 1}; run -all; quit -f'],name)
        assert marker in text;print(marker,flush=True)
    result=dict(passed=True,raster_cases=16,compact_cases=5,cases=data,source_pins=sources,
       scope=__doc__,reference_trace_sha256=ref['trace_sha256'],
       public_sources={str(n.relative_to(ROOT)).replace('\\','/'):sha(n) for n in [Path(__file__),compact]},
       generated_testbench_sha256=sha(a.out/'level179_raster_tb.sv'))
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
