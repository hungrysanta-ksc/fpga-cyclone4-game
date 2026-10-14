# SPDX-License-Identifier: MIT
"""Reuse the existing16x96 history RAM for native lifecycle events (schema A4).

Observation only: no datapath feedback, new memory, commands or timing exceptions.
A NES frame-boundary heartbeat distinguishes stalled ownership from repeated
admission rejection. Ownership/release edges retain brief rejection causes.
"""
from pathlib import Path
import argparse, json
from nes_game147 import ROOT, sha

CHANGED = ['nes_native_export165.sv', 'nes_live_joint.sv',
           'nes_ppu_history157.sv', 'nes_run_observer134.sv', 'fxpak_nes_screen137_top.sv']

def transform(name, s):
    def rep(a, b):
        nonlocal s
        assert s.count(a) == 1, (name, a, s.count(a))
        s = s.replace(a, b)
    if name == 'nes_native_export165.sv':
        rep(' output wire busy,output reg [3:0] error', ' output wire [3:0] observe_state175,\n output wire busy,output reg [3:0] error')
        rep(' assign busy=state!=IDLE;', ' assign observe_state175=state;\n assign busy=state!=IDLE;')
    elif name == 'nes_live_joint.sv':
        rep('output wire out_native_spi_fault,', 'output wire out_native_spi_fault,out_history_valid175,')
        rep('assign out_history157={scanline,cycle,history_flags157,rom_address,game148_hint_physical,ppumem_addr};', '''//175 A4: last16 lifecycle events, not consecutive NES clock samples.
// Frame heartbeat, newly owned lease and release. No observation feeds control.
assign out_history157={8'ha4,native_generation,native_errors,native_export_state175,
 native_initialized,native_active,native_frame_owned,native_geometry_valid,
 native_fill_busy,native_fill_done,native_fill_success,native_fill_error,
 native_export_error,native_row_count,native_group_count,native_object_count,native_palette_count};
reg native_owned_q175;
always @(posedge clk)begin
 if(reset)native_owned_q175<=0;else native_owned_q175<=native_frame_owned;
end
assign out_history_valid175=(tap_ce && scanline==7 && cycle==257) ||
 (native_frame_owned && !native_owned_q175) || native_release_frame;''')
        rep('wire native_host_valid;', 'wire [3:0] native_export_state175;\nwire native_host_valid;')
        rep('nes_native_export165 #(.MAX_CYCLES(33554432)) native_export(',
            'nes_native_export165 #(.MAX_CYCLES(33554432)) native_export(\n .observe_state175(native_export_state175),')
    elif name == 'nes_ppu_history157.sv':
        rep('// Passive last16 NES-clock samples, including the first fault edge.', '//175 Passive last16 enabled lifecycle samples, including first fault edge.')
        rep(' input wire clk,reset,active,freeze,', ' input wire clk,reset,active,freeze,sample_valid175,')
        rep('if(!reset && active && !stopped)entries[next_slot]<=sample;', 'if(!reset && active && !stopped && (sample_valid175 || freeze))entries[next_slot]<=sample;')
        rep('if(active && !stopped)begin', 'if(active && !stopped && (sample_valid175 || freeze))begin')
        # Status version2 identifies event sampling even before A4 records exist.
        rep("8'd1,8'd96,8'd1", "8'd2,8'd96,8'd1")
    elif name == 'nes_run_observer134.sv':
        rep(' input wire [95:0] history_sample157,', ' input wire history_valid175,\n input wire [95:0] history_sample157,')
        rep('nes_ppu_history157 history(.clk(clk),', 'nes_ppu_history157 history(.sample_valid175(history_valid175),.clk(clk),')
    elif name == 'fxpak_nes_screen137_top.sv':
        rep(' wire [95:0] history_sample157;', ' wire [95:0] history_sample157;wire history_valid175;')
        rep('nes_live_joint core(', 'nes_live_joint core(.out_history_valid175(history_valid175),')
        rep('nes_run_observer134 observer(', 'nes_run_observer134 observer(.history_valid175(history_valid175),')
    else:
        raise ValueError(name)
    return s

def prepare(prior, out):
    assert not out.exists() and str(out).isascii()
    pins = json.loads((ROOT/'analysis/errorzero174-verification.json').read_bytes())['sources']
    out.mkdir(parents=True)
    for n,h in pins.items():
        assert sha(prior/n) == h, n
        p=out/n; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((prior/n).read_bytes())
    for n in CHANGED:
        (out/n).write_text(transform(n, (out/n).read_text()), encoding='utf-8', newline='\n')
    r = dict(sources={n:sha(out/n) for n in pins}, baseline=pins, changed=CHANGED,
             public_sources={'tools/nes_lifecycle175.py':sha(Path(__file__))},
             history_schema='A4/native175/lifecycle-events', datapath_control_changed=False,
             extra_memory=False, save_sram_used=False)
    (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n', newline='\n')
    return r

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']: p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args(); prepare(a.prior,a.out)
