# SPDX-License-Identifier: MIT
"""Exercise the real aperture, direct, sink, status and board pin mux in both phases."""
import argparse
import json
import re
from pathlib import Path
import subprocess
from nes_raw506 import once,sha


def main():
    p=argparse.ArgumentParser()
    for k in ('board','fixture','bin','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();d=a.out;d.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1]
    bench=root/'tests/nes-functional'
    src=a.fixture/'top.sv'
    assert sha(src)=='048c534fe281b831422bc1233bf254ed51f29ede918f526d0f8bba67d75f479d'
    for f,h in [('requests.hex','badfa4f3d2ce62be95b717f2b2f85bfb83d04806d60289923ca731274c52ff00'),
                ('fresh.hex','ef8c15fdf26b4f0cf58c90c81e78ecc3b9017b968c9268256333f9ed3fdd549a')]:
        assert sha(a.fixture/f)==h
        (d/f).write_bytes((a.fixture/f).read_bytes())
    (d/'sink-program.hex').write_bytes((a.board/'sink-program.hex').read_bytes())
    s=once(src.read_text(),'reg memory_open=0','reg cpu_drives=0;\nreg memory_open=0')
    # Pre-existing bulk test supplies the physical write data; drive it only on a write grant.
    s=once(s,' reg_write(24\'h604c,1);reg_write(24\'h604d,0);\n'," cpu_drives=1;reg_write(24'h604c,1);reg_write(24'h604d,0);\n")
    s=once(s,'.data_in(wdata),.host_fault','.data_in(SNES_DATA),.host_fault')
    mux=(a.board/'fxpak_nes_screen137_top.sv').read_text()
    mux=mux[mux.index(' assign consumer_oe='):mux.index(' assign SNES_IRQ=')]
    assert mux.count(' assign ')==6
    s=once(s,' nes_direct206 dut(', (bench/'bus571.svh').read_text()+'\n'+(bench/'bus571_latency.svh').read_text()+'\n'+mux+'\n nes_direct206 dut(')
    s=once(s,'  if($test$plusargs("BULK"))','  if($test$plusargs("LAT"))latency571();\n  if($test$plusargs("PINS"))test571();\n  if($test$plusargs("BULK"))')
    (d/'pins.sv').write_text(s)
    matrix=once((bench/'bus571_mux_tb.sv').read_text(),'@FITTED_MUX@',mux)
    (d/'matrix.sv').write_text(matrix)
    modules=json.loads((root/'analysis/gate570-verification.json').read_text())['functional']['local']['modules']
    files=[a.board/name for name in modules]
    files += [a.board/('nes_'+n+'.sv') for n in ('sink_spi165','sink_bus165','sink_bridge165','screen_status151')]
    def run(exe,args,label):
        log=d/(label+'.log')
        with log.open('wb') as f:
            subprocess.run([str(a.bin/(exe+'.exe')),*map(str,args)],cwd=d,check=True,timeout=120,stdout=f,stderr=subprocess.STDOUT)
        return log.read_text(errors='replace')
    run('vlib',['work'],'lib')
    run('vlog',['-sv',*files,d/'pins.sv',d/'matrix.sv'],'compile')
    log=run('vsim',['-c','bus571_mux_tb','-do','run -all; quit -f'],'matrix')
    assert 'PASS571 MUX 128' in log and '** Fatal:' not in log
    latency_ps=[];results=[]
    for ph in (0,1):
        flags=['+GUARDED','+INGRESS','+SHARED']+(['+SHIFT'] if ph else [])
        probe=run('vsim',['-c','gate570_tb',*flags,'+LAT','-do','run -all; quit -f'],'latency'+str(ph))
        assert 'PASS571 LAT' in probe and '** Fatal:' not in probe,probe[-600:]
        times=[int(n) for n in re.findall(r'LAT571 phase=\d elapsed_ps=(\d+)',probe)]
        assert len(times)==4
        latency_ps.append(times)
        for mode,opts,marker in [('bus',['+PINS'],'PASS571 pin_samples=49'),('normal',[],'PASS570 TOP recoveries=5'),
                                 ('consume',['+BULK'],'PASS570 BULK consumes=1'),('partial',['+BULK','+PARTIAL'],'PASS570 BULK consumes=0')]:
            label=mode+str(ph)
            log=run('vsim',['-c','gate570_tb',*flags,*opts,'-do','run -all; quit -f'],label)
            assert marker in log and '** Fatal:' not in log,(label,log[-800:])
            if mode=='normal':assert 'E8570 flags=80 count=0' in log and 'E8570 flags=01 count=0' in log
            results.append([label,marker])
    (d/'result.json').write_text(json.dumps(dict(results=results,latency_ps=latency_ps,mux_cases=128,modules={f.name:sha(f) for f in files},
        top=sha(a.board/'fxpak_nes_screen137_top.sv'),fixture=sha(src)),indent=2)+'\n')


if __name__=='__main__':main()
