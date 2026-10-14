# SPDX-License-Identifier: MIT
"""Long actual-SMB3 collector replay, with an explicitly ideal ROM backend.

Keeps the actual CPU/PPU/mapper and deployed174 collector bytes. Removes the
168MHz physical ROM reader ONLY from the testbench to make scene coverage
practical. Compares the first26 admission rows and frames24/25 pixels with the
archived70ns replay. Not a PSRAM, exporter, SPI, SNES or hardware-speed test.
"""
from pathlib import Path
import argparse, json, re, shutil, subprocess, os
from nes_game147 import ROOT, VHDL, SV, sha

COLLECTORS = ['nes_native_planes165.sv', 'nes_native_compact_planes165.sv',
              'nes_native_raster_frame165.sv', 'nes_native_frame165.sv']
FILES = VHDL + SV + ['cart_nrom.sv', 'nes_probe.sv', 'nes_local_memory.sv',
                   'nes_domain_reset124.sv', 'nes_native_ciram165.sv'] + COLLECTORS


def bench():
    s = (ROOT/'tests/nes-functional/cross174_replay_tb.sv').read_text()
    s = s.replace('initial begin #3.5;forever #2.9761905 mem_clk=~mem_clk;end',
                  '// No physical-memory clock in this admission-only model.')
    a = s.index(' wire [7:0] external_cpu_data,external_ppu_data;')
    b = s.index(' integer target,unused,frame=0', a)
    s = s[:a] + '''
 reg [7:0] prg[0:262143],chr[0:131071];
 wire rom_fault=0;
 wire rom_ppu_valid=!reset && ppumem_addr>=22'h200000 && ppumem_addr<22'h220000;
 wire [7:0] external_cpu_data=cpumem_addr<25'h40000 ? prg[cpumem_addr[17:0]] : 8'hff;
 wire [7:0] external_ppu_data=rom_ppu_valid?chr[ppumem_addr[16:0]]:8'hff;
 nes_local_memory local_memory(.clk(clk),.reset(init_reset),
 .cpumem_addr(cpumem_addr),.cpumem_write(cpumem_write),.cpumem_dout(cpumem_dout),
 .ppumem_addr(ppumem_addr),.ppumem_write(ppumem_write),.ppumem_dout(ppumem_dout),
 .external_cpu_data(external_cpu_data),.external_ppu_data(external_ppu_data),
 .cpumem_din(cpumem_din),.ppumem_din(ppumem_din),.init_done(memory_ready));
''' + s[b:]
    a = s.index(' reg prior_irq=0;')
    b = s.index(' always @(negedge clk)begin', a)
    s = s[:a] + '''
 always @(posedge clk)if(!reset)begin
  ticks++;
  if(rom_cpu_sample && cpumem_addr<25'h40000)begin
   cpu_reads++;prg_banks[cpumem_addr[17:13]]=1;
  end
  if(tap_ce && ppumem_read && rom_ppu_valid)begin
   ppu_reads++;chr_banks[ppumem_addr[16:10]]=1;
  end
  if(tap_mapper_change)mapper_writes++;
 end
''' + s[b:]
    s = s.replace('if(frame>=24)', 'if(frame==24 || frame==25)')
    # A second exact collector sees the same real PPU events, but leases are
    # retained for ten frame periods. It models ownership pressure, not packets.
    names = ['release_frame', 'query', 'query_kind', 'query_index', 'query_generation',
             'frame_owned', 'geometry_valid', 'initialized', 'active', 'response',
             'hit', 'scroll_seen', 'generation', 'errors', 'data', 'row_count',
             'object_count', 'exception_count', 'group_count', 'palette_count']
    def rename(t):
        for n in sorted(names, key=len, reverse=True):
            t = re.sub(r'\bnative_' + n + r'\b', 'slow_' + n, t)
        return t
    declarations = s[s.index('reg native_release_frame'):s.index(' integer native_dump_done')]
    instance = s[s.index('nes_native_frame165 native_frame('):s.rindex('endmodule')]
    instance = rename(instance).replace('native_frame(', 'slow_frame(')
    s = s[:s.rindex('endmodule')] + rename(declarations) + '''
 integer slow_file,slow_capture,slow_count=0;
 initial begin
  slow_release_frame=0;slow_query=0;slow_query_kind=0;slow_query_index=0;slow_query_generation=0;
  slow_file=$fopen("slow-states.tsv","w");
  forever begin
   wait(slow_frame_owned);@(negedge clk);slow_capture=frame;slow_count++;
   $fwrite(slow_file,"%0d %0d %0d %07h %0d %0d %0d %0d %0d %0d\\n",
    slow_generation,frame,slow_geometry_valid,slow_errors,slow_scroll_seen,
    slow_row_count,slow_group_count,slow_object_count,slow_exception_count,slow_palette_count);
   $fflush(slow_file);
   if(slow_geometry_valid)wait(frame>=slow_capture+10);
   @(negedge clk);slow_release_frame=1;@(negedge clk);slow_release_frame=0;
   wait(!slow_frame_owned);
  end
 end
''' + instance + 'endmodule\n'
    return s


def prepare(baseline, out, frames):
    assert not out.exists() and str(out).isascii() and 27 <= frames <= 1200
    pins = json.loads((ROOT/'analysis/cross174-verification.json').read_bytes())['replay_inputs']
    deployed = json.loads((ROOT/'analysis/errorzero174-verification.json').read_bytes())['sources']
    out.mkdir(parents=True)
    for n in FILES + ['prg.hex', 'chr.hex']:
        assert sha(baseline/n) == pins[n], n
        if n in COLLECTORS:
            assert sha(baseline/n) == deployed[n], ('not deployed174 collector', n)
        (out/n).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(baseline/n, out/n)
    (out/'native_frame165_tb.sv').write_text(bench(), encoding='utf-8', newline='\n')
    record = dict(frames=frames, baseline=str(baseline), sources={n:sha(out/n) for n in FILES+['prg.hex','chr.hex','native_frame165_tb.sv']},
                  public_sources={'tools/probe_nes_admission176.py':sha(Path(__file__))},
                  scope='Actual SMB3 CPU/PPU/MMC3 + exact174 collectors, ideal ROM, immediate and10-frame-held leases. No fill/export/SPI/SNES or physical timing.')
    (out/'inputs.json').write_text(json.dumps(record, indent=2)+'\n')


def run(out, questa):
    assert os.environ.get('SALT_LICENSE_SERVER') == '18000@localhost'
    info = json.loads((out/'inputs.json').read_bytes())
    for n,h in info['sources'].items():
        assert sha(out/n) == h, n
    def call(exe, args, label):
        assert not (out/(label+'.log')).exists()
        with (out/(label+'.log')).open('wb') as f:
            p=subprocess.run([str(questa/(exe+'.exe')), *args], cwd=out, stdout=f, stderr=subprocess.STDOUT, timeout=14400)
        text=(out/(label+'.log')).read_text(errors='replace')
        assert p.returncode==0 and not re.search(r'\*\* (Error|Fatal):', text), text[-4000:]
        return text
    call('vlib',['work'],'vlib')
    for i,n in enumerate(VHDL):call('vcom',['-2008',n],f'vcom-{i}')
    call('vlog',['-sv','-mfcu',*[n for n in FILES if n not in VHDL],'native_frame165_tb.sv'],'vlog')
    text=call('vsim',['-c','work.native_frame165_tb',f"+FRAMES={info['frames']}",'-do','onerror {quit -code 1}; run -all; quit -f'],'core')
    assert f"PASS GAME147 frames={info['frames']} " in text
    baseline=Path(info['baseline'])
    old=(baseline/'states.tsv').read_text().splitlines()
    rows=(out/'states.tsv').read_text().splitlines()
    assert rows[:len(old)] == old, 'Ideal ROM changed baseline admission states'
    for frame in [24,25]:
        assert (out/f'game-{frame}.hex').read_text() == (baseline/f'game-{frame}.hex').read_text(), frame
    def summary(name):
        rows=[line.split() for line in (out/name).read_text().splitlines()]
        accepted=[int(r[1]) for r in rows if r[2]=='1']
        rejected={}
        for r in rows:
            if r[2]=='0':rejected[r[3]]=rejected.get(r[3],0)+1
        return dict(samples=len(rows),valid=len(accepted),first_valid=accepted[0] if accepted else None,last_valid=accepted[-1] if accepted else None,rejected_errors=rejected)
    result=dict(completed=True,baseline26_states_equal=True,baseline24_25_pixels_equal=True,
                immediate=summary('states.tsv'),held10=summary('slow-states.tsv'),scope=info['scope'],
                logs={n:sha(out/n) for n in ['core.log','states.tsv','slow-states.tsv']})
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run'])
    p.add_argument('--baseline',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--frames',type=int,default=360);p.add_argument('--questa-bin',type=Path)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.baseline,a.out,a.frames)
    else:run(a.out,a.questa_bin)
